%define debug_package %{nil}

%global  _user          redis
%global  _group         redis
%global  _name          redis
%global  _version       5.0.9
%global  _release       5
%global  _install_dir   /usr/local/%{_name}
%global  _service_name  redis
%global  _working_dir   /var/lib/redis
%global  _pidfile       /var/lib/redis/redis.pid
# %global  _password      redis
%global  _logfile       /var/log/redis/redis.log
%global  _confdir       /etc/redis
%global  _conffile      /etc/redis/redis.cnf

%if !0%{?kylin}
%global  _release %{_release}%{?dist} 
%endif

Name:           %{_name}5
Version:        %{_version}
Release:        %{_release}
BuildArch:      %{_arch}
Summary:        memory database
License:        commodity
Group:          Storage/Memory
URL:            https://redis.io/
Packager:       uuz-repo
# main program..
Source0:        https://download.redis.io/releases/%{_name}-%{version}.tar.gz 
# init scripts
# Source1:      redis
Source2:        redis.cnf
Source3:        redis.service

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
#X-BuildRequires: make gcc jemalloc-devel
BuildRequires:   make gcc jemalloc-devel

%description
Redis is a key-value database. It is similar to memcached but the dataset is not volatile, and values can be strings, exactly like in memcached, but also
lists and sets with atomic operations to push/pop elements.

In order to be very fast but at the same time persistent the whole dataset is taken in memory and from time to time and/or when a number of changes to the
dataset are performed it is written asynchronously on disk. You may lose the last few queries that is acceptable in many applications but it is as fast
as an in memory DB (beta 6 of Redis includes initial support for master-slave replication in order to solve this problem by redundancy).

Compression and other interesting features are a work in progress. Redis is written in ANSI C and works in most POSIX systems like Linux, *BSD, Mac OS X,
and so on. Redis is free software released under the very liberal BSD license.

%prep
%setup -q -n %{_name}-%{version}
rm -frv deps/jemalloc
# Use system jemalloc library
sed -i -e '/cd jemalloc && /d' deps/Makefile
sed -i -e 's|../deps/jemalloc/lib/libjemalloc.a|-ljemalloc -ldl|g' src/Makefile
sed -i -e 's|-I../deps/jemalloc.*|-DJEMALLOC_NO_DEMANGLE -I/usr/include/jemalloc|g' src/Makefile

%if 0%{?with_perftools}
%global malloc_flags    MALLOC=tcmalloc
%else
%global malloc_flags    MALLOC=jemalloc
%endif
%global make_flags      DEBUG="" V="echo" LDFLAGS="%{?__global_ldflags}" CFLAGS+="%{optflags} -fPIC" %{malloc_flags} INSTALL="install -p" PREFIX=%{buildroot}%{_install_dir}

%build
make %{?_smp_mflags} %{make_flags} all

%install
[[ -d %{buildroot} ]] && rm -rf "%{buildroot}"
%{__mkdir} -p "%{buildroot}"
make %{make_flags} install
mkdir -p %{buildroot}/%{_working_dir}
install -p -D -m 644 %{SOURCE2} %{buildroot}/%{_conffile}

%if 0%{?rhel} > 6
install -p -D -m 755 %{SOURCE3} %{buildroot}/usr/lib/systemd/system/%{_service_name}.service
# %else
# install -p -D -m 755 %{SOURCE1} %{buildroot}/etc/init.d/%{_service_name}
%endif

sed -i -e 's|<_install_dir>|%{_install_dir}|g' \
       -e 's|<_service_name>|%{_service_name}|g' \
       -e 's|<_working_dir>|%{_working_dir}|g' \
       -e 's|<_pidfile>|%{_pidfile}|g' \
       -e 's|<_password>|%{_password}|g' \
       -e 's|<_logfile>|%{_logfile}|g' \
       -e 's|<_conffile>|%{_conffile}|g' \
       -e 's|<_user>|%{_user}|g' \
       -e 's|<_group>|%{_group}|g' %{buildroot}/%{_conffile} \
       %if 0%{?rhel} > 6
       %{buildroot}/usr/lib/systemd/system/%{_service_name}.service
       # %else
       # %{buildroot}/etc/init.d/%{_service_name}
       %endif

mkdir -p %{buildroot}/etc/profile.d/
cat > %{buildroot}/etc/profile.d/%{name}.sh<<EOF
export REDIS_BIN_DIR=%{_install_dir}
export PATH=\$PATH:\$REDIS_BIN_DIR/bin
EOF

%clean
%{__rm} -rf "%{buildroot}"

%pre
function mk_custom_user_dir(){
 sysdir=(/bin /boot /etc /home /lib /lib64 /media /mnt /opt /proc /root /run /sbin /srv /sys /tmp /usr /var)
 if [ $(dirname $1) != '/' ] && ! [[ $sysdir =~ $1 ]];
 then
   mk_custom_user_dir $(dirname $1)
 fi
 if [ ! -d $1 ];
 then
   mkdir -p $1
   chown %{_user}:%{_group} $1
 fi
}

case $1 in
  1)
  : install
  getent group %{_group} >/dev/null 2>&1 \
    || groupadd %{_group}

  getent passwd %{_user} >/dev/null 2>&1 \
    || useradd -g %{_group} %{_user}

  mk_custom_user_dir $(dirname %{_install_dir})
  mk_custom_user_dir $(dirname %{_pidfile})
  mk_custom_user_dir $(dirname %{_logfile})
  ;;
  2)
  : update
  ;;
esac

%post
%if 0%{?rhel} > 6 
systemctl daemon-reload
systemctl enable %{_service_name}
#%else
#/sbin/chkconfig --add %{_service_name}
%endif
case $1 in
  1)
  : install
  ;;
  2)
  : update
  ;;
esac

%preun

%if 0%{?rhel} > 6 
 for service_unit in `ls /usr/lib/systemd/system/redis*.service 2>/dev/null || :`
  do
    systemctl stop $(basename ${service_unit}) >/dev/null 2>&1 ||:
  done
#%else
#  for service_name in `ls /etc/init.d/%{_service_name}* 2>/dev/null || :`
#   do 
#    service $(basename ${service_name}) stop >/dev/null 2>&1 ||:
#   done
%endif

case $1 in
  0)
  : uninstall
  ;;
  1)
  : update
  ;;
esac

%postun
%if 0%{?rhel} > 6
systemctl daemon-reload
%endif
case $1 in
  0)
  : uninstall
    for service_name in `ls /etc/init.d/%{_service_name}* 2>/dev/null || :`
    do 
      rm -rf ${service_name}
    done
    for service_unit in `ls /usr/lib/systemd/system/redis*.service 2>/dev/null || :`
    do
      rm -rf ${service_unit}
    done
  ;;
  1)
  : update
  ;;
esac

%files
%defattr(-,%{_user},%{_group})
%{_install_dir}
%{_working_dir}
/etc/profile.d/%{name}.sh
%config(noreplace) %{_confdir}
%if 0%{?rhel} > 6 
%attr(0644,%{_user},%{_group}) /usr/lib/systemd/system/%{_service_name}.service
#%else
#%attr(0755,%{_user},%{_group}) /etc/init.d/%{_service_name}
%endif


%changelog
# By uuz-repo
