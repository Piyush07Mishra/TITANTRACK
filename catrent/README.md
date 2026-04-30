# CatRent Dev Run Guide

This project is a single Django app: backend APIs + frontend templates + admin all run from one server.

## Standard local port
- Default: `8010`
- Dashboard: `http://127.0.0.1:8010/`
- Admin: `http://127.0.0.1:8010/admin/`
- Checkout example: `http://127.0.0.1:8010/checkout/BLD3001/`

## One-command start
From the `catrent` folder:

```bash
./dev_start.sh
```

This will:
1. Load `.env`
2. Run migrations
3. Start server on `127.0.0.1:8010`

## Stop server
```bash
./dev_stop.sh
```

## Check server status
```bash
./dev_status.sh
```

## Optional custom port
You can pass a port manually:

```bash
./dev_start.sh 8003
./dev_stop.sh 8003
./dev_status.sh 8003
```

Or set `DEV_PORT` in your shell before running.
