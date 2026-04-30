# Reminder Automation

## Recommended on this machine: Cron

Launchd may fail with Desktop permission restrictions for background jobs.
Use cron automation instead.

### Install every 2 minutes schedule

```bash
cd "<project>/catrent"
chmod +x automation/*.sh
./automation/install_cron.sh
```

### Verify

```bash
crontab -l
```

### Remove schedule

```bash
./automation/uninstall_cron.sh
```

### Trigger manually now

```bash
set -a && source .env && set +a
./.venv/bin/python manage.py send_rental_remainders
```

### Logs

- `/tmp/catrent-reminders.out.log`
- `/tmp/catrent-reminders.err.log`
