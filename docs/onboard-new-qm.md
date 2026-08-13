# How to Onboard a New Queue Manager

This runbook explains how to safely add a new IBM MQ Queue Manager to MQ-Sentinel.

## Prerequisites

- MQ admin access to the new QM
- Ability to create a SYSTEM.ADMIN.SVRCONN channel with read-only permissions
- Update to the inventory (file or registry)
- OIDC group assignment for the appropriate tier

## Step-by-Step

1. **Gather QM details**
   - Hostname / IP
   - Port (default 1414)
   - Channel name (usually SYSTEM.ADMIN.SVRCONN)
   - SSL/TLS requirements
   - Version (9.2 / 9.3 / 9.4 / z/OS)
   - Environment tier (prod / nonprod)

2. **Create MQ objects (read-only)**
   ```mqsc
   DEFINE CHANNEL(SYSTEM.ADMIN.SVRCONN) CHLTYPE(SVRCONN) TRPTYPE(TCP) +
     MCAUSER('mq-sentinel') SSLCAUTH(REQUIRED)
   
   SET CHLAUTH(SYSTEM.ADMIN.SVRCONN) TYPE(ADDRESSMAP) ADDRESS('*') +
     USERSRC(CHANNEL) CHCKCLNT(REQUIRED)
   
   SET AUTHREC PROFILE('SYSTEM.*') OBJTYPE(QUEUE) +
     PRINCIPAL('mq-sentinel') AUTHADD(DSP)
   ```

3. **Test connectivity from a bastion**
   Use `runmqsc` or the fixture mode first.

4. **Add to inventory**

   Edit your inventory.yaml or ConfigMap:

   ```yaml
   qms:
     - name: NEW_QM_NAME
       host: mq-new.internal
       port: 1414
       channel: SYSTEM.ADMIN.SVRCONN
       ssl: true
       tier: prod   # or nonprod
       description: "Description here"
   ```

5. **Update RBAC (if new tier)**
   Ensure the OIDC groups map correctly to `prod-read` or `nonprod-read`.

6. **Deploy the change**
   - For K8s: Update ConfigMap and rollout.
   - For package install: Restart the service after updating the file.

7. **Verify**

   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     http://mq-sentinel:8080/tools/full_mq_health_check \
     -d '{"qm_name": "NEW_QM_NAME"}'
   ```

   Check that findings appear with correct KC links.

8. **Add monitoring**
   - Confirm the new QM appears in health checks.
   - Update any custom alerts or dashboards.

## Rollback

If the new QM causes issues:
- Remove it from inventory.
- Restart MQ-Sentinel.
- Investigate connection errors in logs.

## Common Issues

- **2035 NOT_AUTHORIZED**: Check MCAUSER and setmqaut.
- **Connection refused**: Firewall / listener not running.
- **SSL errors**: Verify certificates and channel SSL settings.

## Approval

This change should go through your normal change process because it grants (read-only) access to a new production resource.

---

After onboarding, test with your AI agent:

"Run full health check on NEW_QM_NAME and summarize findings with IBM links."