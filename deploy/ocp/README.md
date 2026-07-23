# Deploy EtlNexus to OpenShift (Web Console, no Argo)

Two images from your registry: `etlnexus-backend` (uvicorn, port **8000**, internal) and
`etlnexus-frontend` (nginx, port **8080**, exposed via a Route). The browser talks to the
backend only through the frontend's `/api` proxy.

## Files to drag-and-drop (Import YAML), IN THIS ORDER
Console top-right **`+` → Import YAML** → paste each file, fill the `<...>` placeholders:

1. `pull-secret.yaml`        — registry credentials (`gitlab-pull`)
2. `configmap-backend.yaml`  — backend non-secret env
3. `secret-backend.yaml`     — backend secrets (DB url, SSO secret, LLM key)
4. `configmap-frontend.yaml` — frontend env
5. `backend.yaml`            — backend Deployment + Service (:8000, internal)
6. `frontend.yaml`           — frontend Deployment + Service + Route (:8080, external)

Before importing 5 & 6, set the `image:` line in each to your registry path + tag
(`registry.gitlab.com/<group>/<project>/{backend,frontend}:<tag>`). Do 1–4 first so the
Deployments can reference them by name.

## 3. Deploy the workloads — pick ONE option

### Option A (recommended): Import the full manifests
Both pull from the registry, wire `envFrom`, set ports/probes, and (frontend) create the Route.
Edit the `image:` line in each to your registry path + tag, then **`+` → Import YAML**:
1. `backend.yaml`  — Deployment + Service (ClusterIP :8000, internal)
2. `frontend.yaml` — Deployment + Service (:8080) + Route (external)

They reference `imagePullSecrets: [{name: gitlab-pull}]` and the ConfigMaps/Secret by name —
so create those (steps 1–2) first.

### Option B: the +Add wizard (no YAML)
**+Add → Container images** ×2:
- backend → image `…/backend:<tag>`, name `etlnexus-backend`, port **8000**, **route UNCHECK**,
  Environment → add from `etlnexus-backend-config` + `etlnexus-backend-secret`.
- frontend → image `…/frontend:<tag>`, name `etlnexus-frontend`, port **8080**, **route CHECK**,
  Environment → add from `etlnexus-frontend-config`.

## 5. Wire-up / gotchas
- Backend **Service name** must equal the frontend's `BACKEND_HOST` (`etlnexus-backend`).
- Copy the frontend **Route URL** → that's your public origin. Use it for:
  - Keycloak **Valid Redirect URIs**: `<route-url>/` (SPA-root redirect) and Web Origins `<route-url>`.
  - It is also the value the SPA sends as `redirect_uri` (`window.location.origin` + `/`).
- **Do NOT override command/args** on either deployment — the images' entry points are required
  (the frontend entrypoint runs the nginx envsubst for `BACKEND_HOST`/`CSP_CONNECT_SRC`).
- Env is read at **pod start**. After editing a ConfigMap/Secret, **Actions → Restart rollout**.
- Managed DB: `DB_CREATE_DATABASE=false` (set) + the database must already exist.
- OpenShift runs non-root arbitrary UID → `HOME=/tmp` (set) keeps tools happy. If your project
  enforces `readOnlyRootFilesystem: true`, also mount an `emptyDir` at `/tmp`.
