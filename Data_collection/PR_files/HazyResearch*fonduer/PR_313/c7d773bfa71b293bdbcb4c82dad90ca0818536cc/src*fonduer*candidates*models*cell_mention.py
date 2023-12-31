from typing import Any, Dict, Type

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from fonduer.candidates.models.temporary_context import TemporaryContext
from fonduer.parser.models import Cell
from fonduer.parser.models.context import Context


class TemporaryCellMention(TemporaryContext):
    """The TemporaryContext version of CellMention."""

    def __init__(self, cell: Cell) -> None:
        super().__init__()
        self.cell = cell  # The cell Context

    def __len__(self) -> int:
        return 1

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TemporaryCellMention):
            return NotImplemented
        return self.cell == other.cell

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, TemporaryCellMention):
            return NotImplemented
        return self.cell != other.cell

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, TemporaryCellMention):
            return NotImplemented
        # Allow sorting by comparing the string representations of each
        return self.__repr__() > other.__repr__()

    def __contains__(self, other: object) -> bool:
        if not isinstance(other, TemporaryCellMention):
            return NotImplemented
        return self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.cell)

    def get_stable_id(self) -> str:
        """Return a stable id for the ``CellMention``."""
        return (
            f"{self.cell.document.name}"
            f"::"
            f"{self._get_polymorphic_identity()}"
            f":"
            f"{self.cell.table.position}"
            f":"
            f"{self.cell.position}"
        )

    def _get_table(self) -> Type["CellMention"]:
        return CellMention

    def _get_polymorphic_identity(self) -> str:
        return "cell_mention"

    def _get_insert_args(self) -> Dict[str, Any]:
        return {"cell_id": self.cell.id}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"("
            f"document={self.cell.document.name}, "
            f"table_position={self.cell.table.position}, "
            f"position={self.cell.position}"
            f")"
        )

    def _get_instance(self, **kwargs: Any) -> "TemporaryCellMention":
        return TemporaryCellMention(**kwargs)


class CellMention(Context, TemporaryCellMention):
    """A cell ``Mention``."""

    __tablename__ = "cell_mention"

    #: The unique id of the ``CellMention``.
    id = Column(Integer, ForeignKey("context.id", ondelete="CASCADE"), primary_key=True)

    #: The id of the parent ``Cell``.
    cell_id = Column(Integer, ForeignKey("context.id", ondelete="CASCADE"))

    #: The parent ``Cell``.
    cell = relationship("Context", foreign_keys=cell_id)

    __table_args__ = (UniqueConstraint(cell_id),)

    __mapper_args__ = {
        "polymorphic_identity": "cell_mention",
        "inherit_condition": (id == Context.id),
    }
