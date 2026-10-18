from pathlib import Path
import tomllib

from flutter_agent.skills.catalog import Skill, SkillCatalog


def load_skills(directory: Path) -> SkillCatalog:
    skills: list[Skill] = []
    if not directory.exists():
        return SkillCatalog()
    for path in sorted(directory.glob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        skills.append(
            Skill(
                name=data["name"],
                instructions=data.get("instructions", ""),
                triggers=tuple(data.get("triggers", [])),
            )
        )
    return SkillCatalog(skills)

