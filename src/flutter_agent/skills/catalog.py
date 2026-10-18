from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    instructions: str
    triggers: tuple[str, ...] = ()


class SkillCatalog:
    def __init__(self, skills: list[Skill] | tuple[Skill, ...] = ()):
        self.skills = tuple(skills)

    def select(self, task: str) -> list[Skill]:
        lowered = task.casefold()
        return [skill for skill in self.skills if any(trigger.casefold() in lowered for trigger in skill.triggers)]

