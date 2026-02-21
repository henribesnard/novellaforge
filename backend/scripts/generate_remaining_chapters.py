"""
Script de generation resiliente des chapitres restants via l'API backend.

Usage:
    cd backend
    python -m scripts.generate_remaining_chapters --project-ids <uuid1,uuid2>
    python -m scripts.generate_remaining_chapters --limit 5

Auth:
    --api-token <JWT>  (ou env: NOVELLAFORGE_API_TOKEN / NF_API_TOKEN / API_TOKEN)
    --email / --password (ou env: NOVELLAFORGE_API_EMAIL / NOVELLAFORGE_API_PASSWORD)
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import sys
import traceback
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

# Charger le .env depuis la racine du projet
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(backend_dir)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(root_dir, ".env"))


DEFAULT_API_URL = "http://127.0.0.1:8002/api/v1"
DEFAULT_TIMEOUT = 900
DEFAULT_API_EMAIL = "besnard.hounwanou@gmail.com"
DEFAULT_API_PASSWORD = "NovellaForge-Reset-2026!"
ALLOWED_API_EMAIL = "besnard.hounwanou@gmail.com"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[{_now()}] {message}", flush=True)


def _env_first(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _normalize_api_url(value: Optional[str]) -> str:
    raw = (value or "").strip()
    if not raw:
        raw = DEFAULT_API_URL
    raw = raw.strip().rstrip("/")
    if not raw.endswith("/api/v1"):
        raw = f"{raw}/api/v1"
    return raw


def _probe_api_url(api_url: str, timeout: int) -> bool:
    health_url = f"{api_url.rstrip('/')}/health"
    request = Request(health_url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 400
    except Exception:
        return False


def _parse_port_mapping(value: str) -> Optional[int]:
    raw = value.strip().strip("'\"")
    if not raw or ":" not in raw:
        return None
    parts = raw.split(":")
    if len(parts) < 2:
        return None
    container = parts[-1].split("/")[0]
    host = parts[-2].split("/")[0]
    if container != "8000":
        return None
    try:
        return int(host)
    except ValueError:
        return None


def _extract_backend_port_from_compose(compose_path: str) -> Optional[int]:
    if not os.path.exists(compose_path):
        return None
    try:
        with open(compose_path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return None

    in_backend = False
    in_ports = False
    backend_indent = 0
    ports_indent = 0

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if stripped == "backend:":
            in_backend = True
            in_ports = False
            backend_indent = indent
            continue
        if in_backend and indent <= backend_indent and stripped.endswith(":") and stripped != "backend:":
            in_backend = False
            in_ports = False
        if not in_backend:
            continue
        if stripped.startswith("ports:"):
            in_ports = True
            ports_indent = indent
            continue
        if in_ports:
            if indent <= ports_indent:
                in_ports = False
                continue
            if stripped.startswith("-"):
                mapping = stripped.lstrip("-").strip()
                host_port = _parse_port_mapping(mapping)
                if host_port:
                    return host_port
    return None


def _resolve_api_url(args: argparse.Namespace) -> str:
    candidates: List[str] = []
    if args.api_url:
        candidates.append(_normalize_api_url(args.api_url))
    env_api_url = _env_first("NOVELLAFORGE_API_URL")
    if env_api_url:
        candidates.append(_normalize_api_url(env_api_url))
    frontend_api_url = _env_first("NEXT_PUBLIC_API_URL")
    if frontend_api_url:
        candidates.append(_normalize_api_url(frontend_api_url))
    compose_port = _extract_backend_port_from_compose(os.path.join(root_dir, "docker-compose.yml"))
    if compose_port:
        candidates.append(_normalize_api_url(f"http://localhost:{compose_port}"))
    candidates.append(DEFAULT_API_URL)

    unique_candidates: List[str] = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)

    probe_timeout = max(2, min(5, int(args.timeout)))
    for candidate in unique_candidates:
        log(f"[INIT] Test API: {candidate}")
        if _probe_api_url(candidate, probe_timeout):
            log(f"[INIT] API detectee: {candidate}")
            return candidate
    log(f"[INIT] Aucun endpoint detecte, usage par defaut: {unique_candidates[0]}")
    return unique_candidates[0]


def _parse_project_ids(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    project_ids: List[str] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        project_ids.append(str(UUID(value)))
    return project_ids


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Optional[str]) -> datetime:
    if not value:
        return datetime.min
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.min


def _build_headers(token: Optional[str]) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _read_error_body(error: HTTPError) -> str:
    try:
        body = error.read().decode("utf-8")
    except Exception:
        return ""
    if not body:
        return ""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    detail = payload.get("detail") if isinstance(payload, dict) else payload
    return str(detail or body)


def api_fetch(
    api_url: str,
    path: str,
    token: Optional[str],
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    url = f"{api_url}{path if path.startswith('/') else f'/{path}'}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, method=method, headers=_build_headers(token))
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except HTTPError as exc:
        detail = _read_error_body(exc) or "HTTP error"
        raise RuntimeError(f"API {method} {path} failed (HTTP {exc.code}): {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"API unreachable ({url}): {exc.reason}") from exc


def _login(
    api_url: str,
    email: str,
    password: str,
    timeout: int,
) -> str:
    response = api_fetch(
        api_url,
        "/auth/login/json",
        token=None,
        method="POST",
        payload={"email": email, "password": password},
        timeout=timeout,
    )
    token = response.get("access_token") if isinstance(response, dict) else None
    if not token:
        raise RuntimeError("Impossible de recuperer le token d'authentification.")
    return token


def _fetch_me(api_url: str, token: str, timeout: int) -> Dict[str, Any]:
    response = api_fetch(api_url, "/auth/me", token=token, timeout=timeout)
    return response if isinstance(response, dict) else {}


def _resolve_token(args: argparse.Namespace, api_url: str) -> str:
    token = args.api_token or _env_first("NOVELLAFORGE_API_TOKEN", "NF_API_TOKEN", "API_TOKEN")
    if token:
        return token
    email = args.email or _env_first(
        "NOVELLAFORGE_API_EMAIL", "NF_API_EMAIL", "API_EMAIL"
    ) or DEFAULT_API_EMAIL
    password = args.password or _env_first(
        "NOVELLAFORGE_API_PASSWORD", "NF_API_PASSWORD", "API_PASSWORD"
    ) or DEFAULT_API_PASSWORD
    if email and password:
        log(f"[AUTH] Login via API avec {email}.")
        return _login(api_url, email, password, args.timeout)
    raise RuntimeError(
        "Token manquant. Fournissez --api-token ou --email/--password "
        "(ou variables d'environnement NOVELLAFORGE_API_TOKEN / NOVELLAFORGE_API_EMAIL)."
    )


def _fetch_projects(api_url: str, token: str, limit: Optional[int], timeout: int) -> List[Dict[str, Any]]:
    projects: List[Dict[str, Any]] = []
    skip = 0
    page_size = 100
    while True:
        response = api_fetch(
            api_url,
            f"/projects/?skip={skip}&limit={page_size}",
            token=token,
            timeout=timeout,
        )
        items = response.get("projects") if isinstance(response, dict) else None
        if not items:
            break
        projects.extend(items)
        total = response.get("total", len(projects)) if isinstance(response, dict) else len(projects)
        if limit and len(projects) >= limit:
            projects = projects[:limit]
            break
        if len(projects) >= total:
            break
        skip += page_size
    return projects


def _fetch_project(api_url: str, token: str, project_id: str, timeout: int) -> Dict[str, Any]:
    response = api_fetch(api_url, f"/projects/{project_id}", token=token, timeout=timeout)
    return response if isinstance(response, dict) else {}


def _fetch_plan(api_url: str, token: str, project_id: str, timeout: int) -> Dict[str, Any]:
    response = api_fetch(api_url, f"/projects/{project_id}/plan", token=token, timeout=timeout)
    return response if isinstance(response, dict) else {}


def _fetch_documents(api_url: str, token: str, project_id: str, timeout: int) -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    skip = 0
    page_size = 100
    while True:
        response = api_fetch(
            api_url,
            f"/documents/?project_id={project_id}&skip={skip}&limit={page_size}",
            token=token,
            timeout=timeout,
        )
        items = response.get("documents") if isinstance(response, dict) else None
        if not items:
            break
        documents.extend(items)
        total = response.get("total", len(documents)) if isinstance(response, dict) else len(documents)
        if len(documents) >= total:
            break
        skip += page_size
    return documents


def _extract_plan_chapters(plan_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    plan = plan_payload.get("plan") if isinstance(plan_payload, dict) else None
    chapters = plan.get("chapters") if isinstance(plan, dict) else None
    if not isinstance(chapters, list):
        return []
    cleaned: List[Dict[str, Any]] = []
    for entry in chapters:
        if not isinstance(entry, dict):
            continue
        index = _safe_int(entry.get("index"))
        if not index:
            continue
        cleaned.append({**entry, "index": index})
    cleaned.sort(key=lambda item: item["index"])
    return cleaned


def _document_index(document: Dict[str, Any]) -> Optional[int]:
    metadata = document.get("metadata") if isinstance(document, dict) else None
    metadata = metadata if isinstance(metadata, dict) else {}
    raw_index = metadata.get("chapter_index")
    index = _safe_int(raw_index)
    if index:
        return index
    order_index = _safe_int(document.get("order_index"))
    if order_index is None:
        return None
    return order_index + 1


def _pick_latest_document(documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not documents:
        return None
    approved = [
        doc
        for doc in documents
        if isinstance(doc.get("metadata"), dict)
        and str(doc["metadata"].get("status") or "").lower() == "approved"
    ]
    candidates = approved or documents
    return max(
        candidates,
        key=lambda doc: _parse_datetime(
            (doc.get("updated_at") or doc.get("created_at") or "")
        ),
    )


def _compute_remaining_indices(
    plan_chapters: List[Dict[str, Any]],
    documents: List[Dict[str, Any]],
) -> Tuple[List[int], List[int]]:
    docs_by_index: Dict[int, List[Dict[str, Any]]] = {}
    for doc in documents:
        if str(doc.get("document_type") or "").lower() != "chapter":
            continue
        idx = _document_index(doc)
        if not idx:
            continue
        docs_by_index.setdefault(idx, []).append(doc)

    approved_indices = set()
    for entry in plan_chapters:
        status = str(entry.get("status") or "").lower()
        if status == "approved":
            approved_indices.add(entry["index"])
    for idx, doc_list in docs_by_index.items():
        doc = _pick_latest_document(doc_list)
        if not doc:
            continue
        metadata = doc.get("metadata") if isinstance(doc, dict) else None
        metadata = metadata if isinstance(metadata, dict) else {}
        if str(metadata.get("status") or "").lower() == "approved":
            approved_indices.add(idx)

    plan_indices = [entry["index"] for entry in plan_chapters]
    seen_indices = set()
    remaining_indices: List[int] = []
    for idx in plan_indices:
        if idx in approved_indices or idx in seen_indices:
            continue
        seen_indices.add(idx)
        remaining_indices.append(idx)

    return plan_indices, remaining_indices


def _generate_chapter(
    api_url: str,
    token: str,
    project_id: str,
    chapter_index: int,
    chapter_id: Optional[str],
    use_rag: bool,
    reindex_documents: bool,
    auto_approve: bool,
    timeout: int,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "project_id": project_id,
        "chapter_index": chapter_index,
        "use_rag": use_rag,
        "reindex_documents": reindex_documents,
        "create_document": True,
        "auto_approve": auto_approve,
    }
    if chapter_id:
        payload["chapter_id"] = chapter_id
    response = api_fetch(
        api_url,
        "/writing/generate-chapter",
        token=token,
        method="POST",
        payload=payload,
        timeout=timeout,
    )
    return response if isinstance(response, dict) else {}


def _approve_chapter(
    api_url: str,
    token: str,
    document_id: str,
    timeout: int,
) -> Dict[str, Any]:
    response = api_fetch(
        api_url,
        "/writing/approve-chapter",
        token=token,
        method="POST",
        payload={"document_id": document_id},
        timeout=timeout,
    )
    return response if isinstance(response, dict) else {}


def _process_project(
    api_url: str,
    token: str,
    project_id: str,
    use_rag: bool,
    reindex_documents: bool,
    auto_approve: bool,
    separate_approve: bool,
    approve_retries: int,
    approve_retry_delay: int,
    max_chapters: Optional[int],
    dry_run: bool,
    timeout: int,
) -> None:
    project = _fetch_project(api_url, token, project_id, timeout)
    project_title = project.get("title") or project_id

    try:
        plan_payload = _fetch_plan(api_url, token, project_id, timeout)
    except RuntimeError as exc:
        log(f"[SKIP] Projet {project_title} ({project_id}) plan indisponible: {exc}")
        return
    plan_status = str(plan_payload.get("status") or "draft").lower()
    if plan_status != "accepted":
        log(f"[SKIP] Projet {project_title} ({project_id}) plan non accepte (status={plan_status}).")
        return

    plan_chapters = _extract_plan_chapters(plan_payload)
    if not plan_chapters:
        log(f"[SKIP] Projet {project_title} ({project_id}) plan sans chapitres.")
        return

    documents = _fetch_documents(api_url, token, project_id, timeout)
    plan_indices, remaining_indices = _compute_remaining_indices(plan_chapters, documents)
    if max_chapters:
        remaining_indices = remaining_indices[:max_chapters]

    total = len(plan_indices)
    completed = len(plan_indices) - len(remaining_indices)
    remaining = len(remaining_indices)

    log(
        f"[START] Projet {project_title} ({project_id}) "
        f"- chapitres total={total}, completes={completed}, restants={remaining}"
    )

    if not remaining_indices:
        log(f"[DONE] Projet {project_title} ({project_id}) deja termine.")
        return

    docs_by_index: Dict[int, List[Dict[str, Any]]] = {}
    for doc in documents:
        if str(doc.get("document_type") or "").lower() != "chapter":
            continue
        idx = _document_index(doc)
        if not idx:
            continue
        docs_by_index.setdefault(idx, []).append(doc)

    for idx in remaining_indices:
        doc = _pick_latest_document(docs_by_index.get(idx, []))
        chapter_id = str(doc.get("id")) if doc else None
        doc_metadata = doc.get("metadata") if isinstance(doc, dict) else None
        doc_metadata = doc_metadata if isinstance(doc_metadata, dict) else {}
        doc_status = str(doc_metadata.get("status") or "").lower() if doc else ""

        if auto_approve and separate_approve and doc and doc_status == "draft":
            log(
                f"[RUN] Projet {project_title} ({project_id}) "
                f"- approbation chapitre {idx}/{total} (draft existant)"
            )
            if dry_run:
                log(
                    f"[DRY] Projet {project_title} ({project_id}) "
                    f"- approbation chapitre {idx} ignoree (dry-run)"
                )
                continue

            last_error: Optional[Exception] = None
            for attempt in range(approve_retries + 1):
                if attempt > 0:
                    log(
                        f"[RETRY] Approve chapitre {idx} tentative {attempt}/{approve_retries}"
                    )
                    time.sleep(approve_retry_delay)
                try:
                    response = _approve_chapter(
                        api_url=api_url,
                        token=token,
                        document_id=chapter_id,
                        timeout=timeout,
                    )
                    if not response.get("success", False):
                        raise RuntimeError("approve success=false")
                    completed += 1
                    remaining = max(total - completed, 0)
                    log(
                        f"[OK] Projet {project_title} ({project_id}) "
                        f"- chapitre {idx} approuve. Progression: {completed}/{total} "
                        f"(reste {remaining})"
                    )
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
            if last_error:
                raise RuntimeError(
                    f"Echec approbation chapitre {idx}: {last_error}"
                ) from last_error
            continue

        log(
            f"[RUN] Projet {project_title} ({project_id}) "
            f"- generation chapitre {idx}/{total}"
        )
        if dry_run:
            log(
                f"[DRY] Projet {project_title} ({project_id}) "
                f"- chapitre {idx} ignore (dry-run)"
            )
            continue

        generate_auto_approve = auto_approve and not separate_approve
        result = _generate_chapter(
            api_url=api_url,
            token=token,
            project_id=project_id,
            chapter_index=idx,
            chapter_id=chapter_id,
            use_rag=use_rag,
            reindex_documents=reindex_documents,
            auto_approve=generate_auto_approve,
            timeout=timeout,
        )

        if not result.get("success", False):
            raise RuntimeError(f"Echec generation chapitre {idx}: success=false")

        content = (result.get("content") or "").strip()
        if not content:
            raise RuntimeError(f"Aucun contenu genere pour le chapitre {idx}")

        if auto_approve and separate_approve:
            document_id = result.get("document_id")
            if not document_id:
                raise RuntimeError(f"Aucun document_id pour le chapitre {idx}")
            last_error = None
            for attempt in range(approve_retries + 1):
                if attempt > 0:
                    log(
                        f"[RETRY] Approve chapitre {idx} tentative {attempt}/{approve_retries}"
                    )
                    time.sleep(approve_retry_delay)
                try:
                    response = _approve_chapter(
                        api_url=api_url,
                        token=token,
                        document_id=document_id,
                        timeout=timeout,
                    )
                    if not response.get("success", False):
                        raise RuntimeError("approve success=false")
                    completed += 1
                    remaining = max(total - completed, 0)
                    log(
                        f"[OK] Projet {project_title} ({project_id}) "
                        f"- chapitre {idx} approuve. Progression: {completed}/{total} "
                        f"(reste {remaining})"
                    )
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
            if last_error:
                raise RuntimeError(
                    f"Echec approbation chapitre {idx}: {last_error}"
                ) from last_error
        elif auto_approve:
            completed += 1
            remaining = max(total - completed, 0)
            log(
                f"[OK] Projet {project_title} ({project_id}) "
                f"- chapitre {idx} termine. Progression: {completed}/{total} "
                f"(reste {remaining})"
            )
        else:
            log(
                f"[OK] Projet {project_title} ({project_id}) "
                f"- chapitre {idx} genere (non approuve)."
            )

    log(f"[DONE] Projet {project_title} ({project_id}) termine.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generation resiliente des chapitres restants via API."
    )
    parser.add_argument(
        "--project-ids",
        help="Liste de UUID separes par des virgules.",
        default=None,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limiter le nombre de projets charges.",
    )
    parser.add_argument(
        "--max-chapters",
        type=int,
        default=None,
        help="Limiter le nombre de chapitres traites par projet.",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="URL du backend (ex: http://localhost:8001/api/v1).",
    )
    parser.add_argument(
        "--api-token",
        default=None,
        help="Token JWT (Bearer).",
    )
    parser.add_argument("--email", default=None, help="Email pour login JSON.")
    parser.add_argument("--password", default=None, help="Mot de passe pour login JSON.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Timeout HTTP en secondes (par requete).",
    )
    parser.add_argument(
        "--auto-approve",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Approuver automatiquement les chapitres generes.",
    )
    parser.add_argument(
        "--separate-approve",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Approuver via un appel API separe (plus resilient).",
    )
    parser.add_argument(
        "--approve-retries",
        type=int,
        default=2,
        help="Nombre de tentatives de retry pour l approbation.",
    )
    parser.add_argument(
        "--approve-retry-delay",
        type=int,
        default=20,
        help="Delai (secondes) entre les retries d approbation.",
    )
    parser.add_argument(
        "--use-rag",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Activer la RAG pendant la generation.",
    )
    parser.add_argument(
        "--reindex-documents",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Reindexer les documents avant chaque generation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche le plan d execution sans generer.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    api_url = _resolve_api_url(args)
    log(f"[INIT] API cible: {api_url}")
    token = _resolve_token(args, api_url)

    log("[AUTH] Verification du compte via /auth/me ...")
    me = _fetch_me(api_url, token, args.timeout)
    me_email = str(me.get("email") or "").strip().lower()
    if me_email != ALLOWED_API_EMAIL.lower():
        raise RuntimeError(
            f"Utilisateur non autorise: {me_email or 'inconnu'}. "
            f"Seul {ALLOWED_API_EMAIL} est autorise."
        )
    project_ids = _parse_project_ids(args.project_ids)

    if project_ids:
        projects = [{"id": project_id} for project_id in project_ids]
    else:
        projects = _fetch_projects(api_url, token, args.limit, args.timeout)

    if not projects:
        log("Aucun projet trouve.")
        return

    log(
        f"NovellaForge - generation chapitres restants via API "
        f"(projets={len(projects)})"
    )

    for project in projects:
        project_id = str(project.get("id") or "")
        if not project_id:
            continue
        try:
            _process_project(
                api_url=api_url,
                token=token,
                project_id=project_id,
                use_rag=bool(args.use_rag),
                reindex_documents=bool(args.reindex_documents),
                auto_approve=bool(args.auto_approve),
                separate_approve=bool(args.separate_approve),
                approve_retries=max(0, int(args.approve_retries)),
                approve_retry_delay=max(1, int(args.approve_retry_delay)),
                max_chapters=args.max_chapters,
                dry_run=bool(args.dry_run),
                timeout=args.timeout,
            )
        except Exception as exc:
            log(
                f"[ERROR] Projet {project_id} - erreur sur un chapitre: {exc}"
            )
            traceback.print_exc()
            log("Arret du script. Relancez apres analyse pour reprendre.")
            raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Execution interrompue par l utilisateur.")
        sys.exit(130)
    except Exception as exc:
        log(f"[ERROR] {exc}")
        traceback.print_exc()
        sys.exit(1)
