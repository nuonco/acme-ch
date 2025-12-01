# AGENTS.MD

Listen here you!

## Python

We use UV. Use uv to run python and django commands.

```bash
uv run python manage.py migrate
```

```bash
uv run python manage.py migrate
```

## Apps

Django apps are all nested in the `apps/` directory.

## Templates

The vast majority of the templates will live in `apps/dashboard/templates`. Do not create templates in the root
`templates/` directory if they are rendered by an app's views.

Dashboard templates do no need to live in a dashboard directory within `app/dashboard/templates`.

Dashboard templates should inherit `dashboard-base.html`, not `base.html`.
