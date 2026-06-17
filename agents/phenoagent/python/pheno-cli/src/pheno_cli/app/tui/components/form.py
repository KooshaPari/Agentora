"""
Dynamic form builder component.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import HAS_TEXTUAL, Checkbox, ComposeResult, Container, Input, Select, Static
from .config import ComponentTheme

if TYPE_CHECKING:
    from collections.abc import Callable


class FormBuilder(Container if HAS_TEXTUAL else object):
    """
    Dynamic form builder with validation.
    """

    def __init__(
        self,
        title: str = "Form",
        fields: list[dict[str, Any]] | None = None,
        theme: ComponentTheme = ComponentTheme.DEFAULT,
        **kwargs: Any,
    ):
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.title = title
        self.fields = fields or []
        self.theme = theme
        self.values: dict[str, Any] = {}
        self.errors: dict[str, str] = {}

    def add_field(
        self,
        name: str,
        field_type: str,
        label: str,
        default: Any = "",
        required: bool = False,
        options: list[str] | None = None,
        validator: Callable[[Any], bool] | None = None,
    ) -> None:
        """
        Add a field to the form.
        """
        field = {
            "name": name,
            "type": field_type,
            "label": label,
            "default": default,
            "required": required,
            "options": options or [],
            "validator": validator,
        }
        self.fields.append(field)
        self.values[name] = default

    def compose(self) -> ComposeResult:
        """
        Compose form UI.
        """
        if not HAS_TEXTUAL:
            return []

        yield Static(f"[bold]{self.title}[/bold]", id="form-title")

        for field in self.fields:
            name = field["name"]
            field_type = field["type"]
            label = field["label"]
            required_marker = " *" if field.get("required") else ""

            yield Static(f"{label}{required_marker}:", id=f"label-{name}")

            if field_type == "text":
                yield Input(placeholder=label, id=f"input-{name}")
            elif field_type == "select":
                options = [(opt, opt) for opt in field.get("options", [])]
                yield Select(options, id=f"select-{name}")
            elif field_type == "checkbox":
                yield Checkbox(label, id=f"checkbox-{name}")
            elif field_type == "textarea":
                yield Input(placeholder=label, id=f"textarea-{name}")

    def validate(self) -> bool:
        """
        Validate all form fields.
        """
        self.errors.clear()
        valid = True

        for field in self.fields:
            name = field["name"]
            value = self.values.get(name)

            if field.get("required") and not value:
                self.errors[name] = "This field is required"
                valid = False
                continue

            validator = field.get("validator")
            if validator and value:
                try:
                    if not validator(value):
                        self.errors[name] = "Invalid value"
                        valid = False
                except Exception as exc:  # pragma: no cover - defensive validation
                    self.errors[name] = str(exc)
                    valid = False

        return valid

    def get_values(self) -> dict[str, Any]:
        """
        Return a copy of current form values.
        """
        return self.values.copy()


__all__ = ["FormBuilder"]
