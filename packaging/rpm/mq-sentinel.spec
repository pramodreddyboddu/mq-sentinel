# MQ-Sentinel RPM spec — for RHEL 9 / Rocky 9 / OEL 9 / Amazon Linux 2023.
#
# Build (from repo root):
#   make rpm                   # uses fpm — easiest path
#   rpmbuild -bb packaging/rpm/mq-sentinel.spec  # native, requires rpmbuild
#
# The native rpmbuild path expects:
#   - /tmp/mq-sentinel-%{version}/  pre-staged build tree (SOURCE0)
#   - python3.12 available at build time
#
# pymqi is intentionally NOT a hard Requires — IBM MQ client install is
# customer-controlled (see docs/byom.md). Without it, MQ-Sentinel still
# runs in fixture / demo mode.

Name:           mq-sentinel
Version:        0.1.0
Release:        1%{?dist}
Summary:        Read-only IBM MQ diagnostic MCP server (enterprise)
License:        Proprietary
URL:            https://github.com/pramodreddyboddu/mq-sentinel
Source0:        %{name}-%{version}.tar.gz
BuildArch:      x86_64

BuildRequires:  python3.12 >= 3.12
BuildRequires:  python3.12-devel
BuildRequires:  systemd-rpm-macros

Requires:       python3.12 >= 3.12
Requires:       systemd
Requires:       (shadow-utils or shadow)

%{?systemd_requires}

%description
MQ-Sentinel is a read-only, enterprise-grade IBM MQ diagnostic MCP server.
It returns Root Cause Summaries with IBM Knowledge Center references for
every IBM MQ deployment flavor (Standalone, Multi-Instance, RDQM, Native
HA + CRR, Uniform Cluster, Traditional Cluster, z/OS QSG, MQ Appliance,
Containerized) — read-only by construction.

%prep
%setup -q

%build
python3.12 -m venv %{_builddir}/venv
%{_builddir}/venv/bin/pip install --upgrade pip wheel
%{_builddir}/venv/bin/pip install --no-cache-dir .

%install
rm -rf %{buildroot}

# Application
install -d -m 0755 %{buildroot}/opt/mq-sentinel/bin
install -d -m 0755 %{buildroot}/opt/mq-sentinel/lib

# Bundle the venv (relocatable Python install)
cp -a %{_builddir}/venv/. %{buildroot}/opt/mq-sentinel/

# Convenience launcher with the right venv on PATH
cat >%{buildroot}/opt/mq-sentinel/bin/mq-sentinel-launcher <<'EOF'
#!/bin/sh
exec /opt/mq-sentinel/bin/mq-sentinel "$@"
EOF
chmod 0755 %{buildroot}/opt/mq-sentinel/bin/mq-sentinel-launcher

# Symlink into PATH
install -d -m 0755 %{buildroot}%{_bindir}
ln -sf /opt/mq-sentinel/bin/mq-sentinel %{buildroot}%{_bindir}/mq-sentinel

# systemd unit + env file
install -d -m 0755 %{buildroot}%{_unitdir}
install -m 0644 packaging/systemd/mq-sentinel.service %{buildroot}%{_unitdir}/mq-sentinel.service

install -d -m 0750 %{buildroot}%{_sysconfdir}/mq-sentinel
install -d -m 0700 %{buildroot}%{_sysconfdir}/mq-sentinel/secrets
install -d -m 0750 %{buildroot}%{_sysconfdir}/mq-sentinel/inventory
install -m 0640 packaging/systemd/mq-sentinel.env %{buildroot}%{_sysconfdir}/mq-sentinel/mq-sentinel.env

# Audit log dir (writable)
install -d -m 0750 %{buildroot}%{_localstatedir}/log/mq-sentinel

# Docs
install -d -m 0755 %{buildroot}%{_docdir}/%{name}
install -m 0644 README.md SECURITY.md CHANGELOG.md LICENSE %{buildroot}%{_docdir}/%{name}/
cp -r docs %{buildroot}%{_docdir}/%{name}/docs

%pre
getent group mq-sentinel >/dev/null || groupadd -r mq-sentinel
getent passwd mq-sentinel >/dev/null || \
    useradd -r -g mq-sentinel -d /opt/mq-sentinel -s /sbin/nologin \
            -c "MQ-Sentinel service account" mq-sentinel

%post
%systemd_post mq-sentinel.service
chown -R mq-sentinel:mq-sentinel /var/log/mq-sentinel
chown -R root:mq-sentinel /etc/mq-sentinel
chown -R root:mq-sentinel /etc/mq-sentinel/secrets

cat <<'BANNER'
================================================================================
  MQ-Sentinel installed.

  Next steps:
    1. Edit /etc/mq-sentinel/mq-sentinel.env — set MQS_AUTH_OIDC_* values.
    2. Drop QM credentials in /etc/mq-sentinel/secrets/<ref>/{username,password}
       (chmod 400 files, chmod 700 dirs, owner: mq-sentinel:mq-sentinel).
    3. Edit /etc/mq-sentinel/inventory/inventory.yaml.
    4. systemctl enable --now mq-sentinel
    5. journalctl -u mq-sentinel -f

  For air-gapped sites, see /usr/share/doc/mq-sentinel/docs/byom.md
================================================================================
BANNER

%preun
%systemd_preun mq-sentinel.service

%postun
%systemd_postun_with_restart mq-sentinel.service
if [ $1 -eq 0 ]; then
    # Full uninstall (not upgrade) — keep audit logs & config.
    echo "MQ-Sentinel removed. /var/log/mq-sentinel and /etc/mq-sentinel preserved."
fi

%files
%license LICENSE
%doc %{_docdir}/%{name}
/opt/mq-sentinel
%{_bindir}/mq-sentinel
%{_unitdir}/mq-sentinel.service
%dir %attr(0750, root, mq-sentinel) %{_sysconfdir}/mq-sentinel
%dir %attr(0700, root, mq-sentinel) %{_sysconfdir}/mq-sentinel/secrets
%dir %attr(0750, root, mq-sentinel) %{_sysconfdir}/mq-sentinel/inventory
%config(noreplace) %attr(0640, root, mq-sentinel) %{_sysconfdir}/mq-sentinel/mq-sentinel.env
%dir %attr(0750, mq-sentinel, mq-sentinel) %{_localstatedir}/log/mq-sentinel

%changelog
* Wed Apr 30 2026 MG <noreply@example.com> - 0.1.0-1
- Initial RPM packaging.
- Bundles venv at /opt/mq-sentinel; systemd unit + hardened service file.
- Service account mq-sentinel:mq-sentinel created in %pre.
