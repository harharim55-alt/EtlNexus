# EtlNexus Helm chart

Deploys both services: **backend** (FastAPI/uvicorn, :8000, internal ClusterIP) and
**frontend** (React/nginx, :8080, exposed via an OpenShift Route). The browser reaches the
backend only through the frontend's `/api` proxy.

## Renders
- ConfigMap + Secret (backend env, split secret/non-secret)
- ConfigMap (frontend env; `BACKEND_HOST` auto-wired to the backend Service)
- Deployment + Service (backend, frontend)
- Route (frontend; disable with `frontend.route.enabled=false` to use an Ingress)
- Image pull Secret (`imagePullSecret.create=true`)

## Install / upgrade
```
oc login <cluster-url> --token=<token>
helm upgrade --install etlnexus ./deploy/helm/etlnexus -n <namespace> --create-namespace \
  -f my-values.yaml
```
`my-values.yaml` overrides the placeholders (registry, DB, SSO, etc.). Keep secrets out of git —
pass them with `--set-string` or a separate untracked values file:
```
helm upgrade --install etlnexus ./deploy/helm/etlnexus -n <ns> \
  --set imageRegistry=registry.gitlab.com/acme/etlnexus \
  --set backend.image.tag=2026-07-09 --set frontend.image.tag=2026-07-09 \
  --set-string imagePullSecret.username=<user> --set-string imagePullSecret.token=<token> \
  --set-string backend.secretEnv.DATABASE_URL='postgresql+asyncpg://u:p@host:5432/db' \
  --set-string backend.secretEnv.SSO_CLIENT_SECRET='<secret>'
```

## Must-set values
- `imageRegistry`, `backend.image.tag`, `frontend.image.tag` (use a **unique tag** per build).
- `imagePullSecret.username` / `.token` (private registry).
- `backend.secretEnv.DATABASE_URL`, `backend.secretEnv.SSO_CLIENT_SECRET`.
- `backend.env.SSO_ISSUER_URL` / `SSO_PUBLIC_ISSUER_URL`, `SPARK_CONNECT_URL`, `CORS_ORIGINS`.
- `frontend.env.CSP_CONNECT_SRC` (Keycloak origin).

## Notes
- Managed DB → `backend.env.DB_CREATE_DATABASE="false"` (default) + the DB must already exist.
- OpenShift non-root UID: `HOME=/tmp` (general writable home, not uv) + no `command` override. No uv at runtime.
- After deploy, get the Route URL (`oc get route etlnexus`) → register in Keycloak
  (redirect `<url>/`, Web Origins) — it's the SPA's `redirect_uri`.
- **Argo CD** can point straight at this chart path instead of `helm` CLI.

## Validate before applying
```
helm lint ./deploy/helm/etlnexus
helm template etlnexus ./deploy/helm/etlnexus -f my-values.yaml   # inspect rendered manifests
```
