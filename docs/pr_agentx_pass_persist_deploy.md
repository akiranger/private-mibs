PR: Add pass_persist integration and deployment docs

Summary

This PR implements a pragmatic integration path between net-snmp (snmpd) and the generated Python MIB handlers using net-snmp's pass_persist mechanism. It adds:

- scaffold/agentx_pass_persist.py — pass_persist helper that maps OIDs to scaffold/generated_handlers/<name>.py handlers
- scaffold/agentx_mapping.example.json — example OID -> handler mapping
- scaffold/generated_handlers/myScalar.py — demo handler used for smoke tests
- docs/agentx_integration_full.md — detailed integration and testing guide
- docs/snmpd_systemd_examples.md — snmpd.conf and systemd unit examples for deployment
- README.md — short deployment steps and reviewer guidance

Reviewer checklist

- [ ] Confirm docs describe a safe deployment (recommend SNMPv3 for production)
- [ ] Verify agentx_pass_persist.py loads handlers from scaffold/generated_handlers correctly
- [ ] Smoke test instructions reproduce expected behavior locally

Notes

- This PR introduces a short-term integration approach (pass_persist). For high-performance or advanced AgentX features, refer to follow-up issues in the repo for C-based subagent migration and transactional persistence.
