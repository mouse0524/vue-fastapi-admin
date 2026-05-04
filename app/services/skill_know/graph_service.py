from __future__ import annotations

from fastapi import HTTPException
from tortoise.expressions import Q

from app.models.admin import SkillKnowContextRelation, SkillKnowDocument, SkillKnowSkill


class SkillKnowGraphService:
    async def record(
        self,
        *,
        source_uri: str,
        target_uri: str,
        relation_type: str = "related_to",
        reason: str = "",
        weight: float = 1.0,
        metadata: dict | None = None,
    ) -> dict:
        if not source_uri or not target_uri:
            raise HTTPException(status_code=400, detail="source_uri 和 target_uri 不能为空")
        relation = await SkillKnowContextRelation.filter(
            source_uri=source_uri,
            target_uri=target_uri,
            relation_type=relation_type,
        ).first()
        if relation:
            relation.reason = reason or relation.reason
            relation.weight = weight
            relation.extra_metadata = metadata or relation.extra_metadata or {}
            await relation.save()
        else:
            relation = await SkillKnowContextRelation.create(
                source_uri=source_uri,
                target_uri=target_uri,
                relation_type=relation_type,
                reason=reason,
                weight=weight,
                extra_metadata=metadata or {},
            )
        return await relation.to_dict()

    async def delete(self, relation_id: int) -> None:
        deleted = await SkillKnowContextRelation.filter(id=relation_id).delete()
        if not deleted:
            raise HTTPException(status_code=404, detail="关系不存在")

    async def cleanup_uri(self, uri: str) -> None:
        await SkillKnowContextRelation.filter(Q(source_uri=uri) | Q(target_uri=uri)).delete()

    async def relations(self, uri: str | None = None, relation_type: str | None = None, limit: int = 200) -> list[dict]:
        q = Q()
        if uri:
            q &= Q(source_uri=uri) | Q(target_uri=uri)
        if relation_type:
            q &= Q(relation_type=relation_type)
        rows = await SkillKnowContextRelation.filter(q).order_by("-weight", "-id").limit(limit)
        return [await item.to_dict() for item in rows]

    async def first_hop(self, uris: list[str], limit_per_uri: int = 5) -> dict[str, list[dict]]:
        if not uris:
            return {}
        rows = await SkillKnowContextRelation.filter(source_uri__in=uris).order_by("-weight", "-id")
        result: dict[str, list[dict]] = {}
        for row in rows:
            items = result.setdefault(row.source_uri, [])
            if len(items) >= limit_per_uri:
                continue
            items.append({
                "id": row.id,
                "target_uri": row.target_uri,
                "relation_type": row.relation_type,
                "reason": row.reason,
                "weight": row.weight,
                "metadata": row.extra_metadata or {},
            })
        return result

    async def graph(self, *, center_uri: str | None = None, depth: int = 2, limit: int = 200) -> dict:
        depth = max(1, min(depth, 3))
        if center_uri:
            visited = {center_uri}
            frontier = {center_uri}
            relations = []
            for _ in range(depth):
                rows = await SkillKnowContextRelation.filter(Q(source_uri__in=list(frontier)) | Q(target_uri__in=list(frontier))).limit(limit)
                next_frontier = set()
                for row in rows:
                    relations.append(row)
                    if row.source_uri not in visited:
                        next_frontier.add(row.source_uri)
                    if row.target_uri not in visited:
                        next_frontier.add(row.target_uri)
                visited.update(next_frontier)
                frontier = next_frontier
                if not frontier:
                    break
        else:
            relations = await SkillKnowContextRelation.all().order_by("-weight", "-id").limit(limit)

        uri_set = {rel.source_uri for rel in relations} | {rel.target_uri for rel in relations}
        nodes = await self._nodes(uri_set)
        edges = [
            {
                "id": rel.id,
                "source": rel.source_uri,
                "target": rel.target_uri,
                "type": rel.relation_type,
                "label": rel.relation_type,
                "reason": rel.reason,
                "weight": rel.weight,
            }
            for rel in relations
        ]
        return {"nodes": list(nodes.values()), "edges": edges, "total": len(edges)}

    async def _nodes(self, uris: set[str]) -> dict[str, dict]:
        nodes: dict[str, dict] = {}
        if not uris:
            return nodes
        skills = await SkillKnowSkill.filter(uri__in=list(uris))
        for skill in skills:
            nodes[skill.uri] = {
                "id": skill.uri,
                "uri": skill.uri,
                "label": skill.name,
                "type": "skill",
                "category": str(skill.category),
                "abstract": skill.abstract or skill.description,
            }
        documents = await SkillKnowDocument.filter(uri__in=list(uris))
        for doc in documents:
            nodes[doc.uri] = {
                "id": doc.uri,
                "uri": doc.uri,
                "label": doc.title,
                "type": "document",
                "category": doc.category,
                "abstract": doc.abstract or doc.description,
            }
        for uri in uris:
            nodes.setdefault(uri, {"id": uri, "uri": uri, "label": uri.split("/")[-1], "type": "context"})
        return nodes


skill_know_graph_service = SkillKnowGraphService()
