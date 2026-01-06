# Documentation Index

Complete documentation for Remington - Autonomous Project Manager Agent.

---

## 🚀 Getting Started

### Setup Guides

**[Atlassian Bot Setup](ATLASSIAN_BOT_SETUP.md)**
- Create dedicated service account for Jira/Bitbucket
- Configure bot user permissions
- Generate API tokens
- **Read this first** if deploying to production

**[Slack Bot Setup](SLACK_BOT_SETUP.md)**
- Create Slack app and bot user
- Configure OAuth scopes and permissions
- Get bot token and user ID
- Set up event subscriptions

**[Webhook Setup](WEBHOOK_SETUP.md)**
- Configure Jira webhooks for instant notifications
- Register webhook endpoints
- Test webhook delivery
- **Optional but recommended** for production

**[Scheduling Setup](SCHEDULING_SETUP.md)**
- Set up cron jobs for daily standup (9 AM)
- Configure systemd timers for hourly SLA checks
- Options for different operating systems
- **Required** for automated workflows

---

## 🏗️ Architecture

**[Hybrid Architecture](architecture/HYBRID_ARCHITECTURE.md)**
- Webhook + Polling hybrid approach
- Why we use both systems
- System components and data flow
- Performance characteristics

---

## 🚀 Deployment

**[Deployment Checklist](deployment/DEPLOYMENT_CHECKLIST.md)**
- Pre-deployment verification steps
- Environment variable validation
- API key requirements
- Production readiness checklist

**[Heroku Deployment Guide](deployment/HEROKU_DEPLOYMENT.md)**
- Deploy to Heroku with dual-dyno architecture
- Configure environment variables
- Set up clock dyno for scheduled tasks
- Monitoring and logging

---

## 🧪 Testing

**[Integration Test Plan](testing/INTEGRATION_TEST_PLAN.md)**
- Comprehensive test scenarios
- API integration tests
- End-to-end workflow tests
- Expected outcomes and verification

**[Manual Test Guide](testing/MANUAL_TEST.md)**
- Step-by-step testing procedures
- Verify component initialization
- Test Jira/Slack/Bitbucket monitoring
- Validate orchestrator responses

**[Interactive Test Guide](testing/INTERACTIVE_TEST_GUIDE.md)**
- Manual interaction tests
- Context preservation verification
- Thread-based conversation testing
- Real-world usage scenarios

**[Test Plan](testing/TEST_PLAN.md)**
- Complete test coverage matrix
- Polling & event detection tests
- SLA enforcement tests
- Automated workflow tests

---

## 📝 Quick Reference

### Essential Reading (In Order)

1. **Main [README.md](../README.md)** - Start here for overview and quick start
2. **[Atlassian Bot Setup](ATLASSIAN_BOT_SETUP.md)** - Create service account
3. **[Slack Bot Setup](SLACK_BOT_SETUP.md)** - Set up Slack integration
4. **[Deployment Checklist](deployment/DEPLOYMENT_CHECKLIST.md)** - Pre-launch verification
5. **[Manual Test Guide](testing/MANUAL_TEST.md)** - Verify everything works

### For Production Deployment

- [Webhook Setup](WEBHOOK_SETUP.md) - Configure instant notifications
- [Scheduling Setup](SCHEDULING_SETUP.md) - Automate daily/hourly jobs
- [Heroku Deployment](deployment/HEROKU_DEPLOYMENT.md) - Cloud deployment option

### For Developers

- [Hybrid Architecture](architecture/HYBRID_ARCHITECTURE.md) - System design
- [Integration Test Plan](testing/INTEGRATION_TEST_PLAN.md) - Test strategy
- [Test Plan](testing/TEST_PLAN.md) - Coverage matrix

---

## 🔗 External Resources

- **Main README**: [../README.md](../README.md)
- **Contributing Guide**: [../CONTRIBUTING.md](../CONTRIBUTING.md)
- **License**: [../LICENSE](../LICENSE)
- **GitHub Issues**: [https://github.com/ethandrower/remington/issues](https://github.com/ethandrower/remington/issues)

---

**Last Updated**: January 2026
