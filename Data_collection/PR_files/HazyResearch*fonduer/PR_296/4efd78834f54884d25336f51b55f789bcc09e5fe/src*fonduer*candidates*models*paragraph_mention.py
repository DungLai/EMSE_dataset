from typing import Any, Dict, Type

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from fonduer.candidates.models.temporary_context import TemporaryContext
from fonduer.parser.models import Paragraph
from fonduer.parser.models.context import Context


class TemporaryParagraphMention(TemporaryContext):
    """The TemporaryContext version of ParagraphMention."""

    def __init__(self, paragraph: Paragraph) -> None:
        super(TemporaryParagraphMention, self).__init__()
        self.paragraph = paragraph  # The paragraph Context

    def __len__(self) -> int:
        return 1

    def __eq__(self, other):
        try:
            return self.paragraph == other.paragraph
        except AttributeError:
            return False

    def __ne__(self, other):
        try:
            return self.paragraph != other.paragraph
        except AttributeError:
            return True

    def __gt__(self, other: "TemporaryParagraphMention") -> bool:
        # Allow sorting by comparing the string representations of each
        return self.__repr__() > other.__repr__()

    def __contains__(self, other_paragraph: "TemporaryParagraphMention") -> bool:
        return self.__eq__(other_paragraph)

    def __hash__(self) -> int:
        return hash(self.paragraph)

    def get_stable_id(self) -> str:
        """Return a stable id for the ``ParagraphMention``."""
        return (
            f"{self.paragraph.document.name}"
            f"::"
            f"{self._get_polymorphic_identity()}"
            f":"
            f"{self.paragraph.position}"
        )

    def _get_table(self) -> Type["ParagraphMention"]:
        return ParagraphMention

    def _get_polymorphic_identity(self) -> str:
        return "paragraph_mention"

    def _get_insert_args(self) -> Dict[str, Any]:
        return {"paragraph_id": self.paragraph.id}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"("
            f"document={self.paragraph.document.name}, "
            f"position={self.paragraph.position}"
            f")"
        )

    def _get_instance(self, **kwargs: Any) -> "TemporaryParagraphMention":
        return TemporaryParagraphMention(**kwargs)


class ParagraphMention(Context, TemporaryParagraphMention):
    """A paragraph ``Mention``."""

    __tablename__ = "paragraph_mention"

    #: The unique id of the ``ParagraphMention``.
    id = Column(Integer, ForeignKey("context.id", ondelete="CASCADE"), primary_key=True)

    #: The id of the parent ``Paragraph``.
    paragraph_id = Column(Integer, ForeignKey("context.id", ondelete="CASCADE"))

    #: The parent ``Paragraph``.
    paragraph = relationship("Context", foreign_keys=paragraph_id)

    __table_args__ = (UniqueConstraint(paragraph_id),)

    __mapper_args__ = {
        "polymorphic_identity": "paragraph_mention",
        "inherit_condition": (id == Context.id),
    }
