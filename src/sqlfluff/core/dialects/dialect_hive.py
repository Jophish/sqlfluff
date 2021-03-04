"""The Hive dialect."""

from sqlfluff.core.parser import (
    BaseSegment,
    Sequence,
    Ref,
    OneOf,
    Bracketed,
    Delimited,
    StartsWith,
    NamedSegment,
)

from sqlfluff.core.dialects.dialect_ansi import ansi_dialect
from sqlfluff.core.dialects.hive_keywords import RESERVED_KEYWORDS, UNRESERVED_KEYWORDS

hive_dialect = ansi_dialect.copy_as("hive")

# Clear ANSI Keywords and add all Hive keywords
# hive_dialect.sets("unreserved_keywords").clear()
hive_dialect.sets("unreserved_keywords").update(UNRESERVED_KEYWORDS)
# hive_dialect.sets("reserved_keywords").clear()
hive_dialect.sets("reserved_keywords").update(RESERVED_KEYWORDS)

hive_dialect.sets("bracket_pairs").update(
    [
        # NB: Angle brackets can be mistaken, so False
        ("angle", "LessThanSegment", "GreaterThanSegment", False)
    ]
)


hive_dialect.add(
    DoubleQuotedLiteralSegment=NamedSegment.make(
        "double_quote", name="quoted_literal", type="literal", trim_chars=('"',)
    ),
    SingleOrDoubleQuotedLiteralGrammar=OneOf(
        Ref("QuotedLiteralSegment"), Ref("DoubleQuotedLiteralSegment")
    ),
    LocationGrammar=Sequence("LOCATION", Ref("QuotedLiteralSegment")),
    PropertyGrammar=Sequence(
        Ref("SingleOrDoubleQuotedLiteralGrammar"),
        Ref("EqualsSegment"),
        Ref("SingleOrDoubleQuotedLiteralGrammar"),
    ),
    TablePropertiesGrammar=Sequence(
        "TBLPROPERTIES", Bracketed(Delimited(Ref("PropertyGrammar")))
    ),
    SerdePropertiesGrammar=Sequence(
        "WITH", "SERDEPROPERTIES", Bracketed(Delimited(Ref("PropertyGrammar")))
    ),
    TerminatedByGrammar=Sequence("TERMINATED", "BY", Ref("QuotedLiteralSegment")),
    FileFormatGrammar=OneOf(
        "SEQUENCEFILE",
        "TEXTFILE",
        "RCFILE",
        "ORC",
        "PARQUET",
        "AVRO",
        "JSONFILE",
        Sequence(
            "INPUTFORMAT",
            Ref("QuotedLiteralSegment"),
            "OUTPUTFORMAT",
            Ref("QuotedLiteralSegment"),
        ),
    ),
    StoredAsGrammar=Sequence("STORED", "AS", Ref("FileFormatGrammar")),
    StoredByGrammar=Sequence(
        "STORED",
        "BY",
        Ref("QuotedLiteralSegment"),
        Ref("SerdePropertiesGrammar", optional=True),
    ),
    StorageFormatGrammar=OneOf(
        Sequence(
            Ref("RowFormatClauseSegment", optional=True),
            Ref("StoredAsGrammar", optional=True),
        ),
        Ref("StoredByGrammar"),
    ),
)


@hive_dialect.segment(replace=True)
class CreateTableStatementSegment(BaseSegment):
    """A `CREATE TABLE` statement."""

    type = "create_table_statement"
    match_grammar = StartsWith(
        Sequence(
            "CREATE",
            Ref.keyword("EXTERNAL", optional=True),
            Ref.keyword("TEMPORARY", optional=True),
            "TABLE",
        )
    )

    parse_grammar = Sequence(
        "CREATE",
        Ref.keyword("EXTERNAL", optional=True),
        Ref.keyword("TEMPORARY", optional=True),
        "TABLE",
        Ref("IfNotExistsGrammar", optional=True),
        Ref("TableReferenceSegment"),
        OneOf(
            # Columns and comment syntax:
            Sequence(
                Bracketed(
                    Delimited(
                        OneOf(
                            Ref("TableConstraintSegment"),
                            Ref("ColumnDefinitionSegment"),
                        ),
                    )
                ),
                Sequence(  # [COMMENT 'string']
                    "COMMENT", Ref("QuotedLiteralSegment"), optional=True
                ),
                Sequence(  # [PARTITONED BY (col_name data_type [COMMENT col_comment], ...)]
                    "PARTITIONED",
                    "BY",
                    Bracketed(Delimited(Ref("ColumnDefinitionSegment"))),
                    optional=True,
                ),
                Sequence(
                    "CLUSTERED",
                    "BY",
                    Ref("BracketedColumnReferenceListGrammar"),
                    Sequence(
                        "SORTED",
                        "BY",
                        Bracketed(
                            Delimited(
                                Sequence(
                                    Ref("ColumnReferenceSegment"),
                                    OneOf("ASC", "DESC", optional=True),
                                )
                            )
                        ),
                        optional=True,
                    ),
                    "INTO",
                    Ref("NumericLiteralSegment"),
                    "BUCKETS",
                    optional=True,
                ),
                Ref("SkewedByClauseSegment", optional=True),
                Ref("StorageFormatGrammar", optional=True),
                Ref("LocationGrammar", optional=True),
                Ref("TablePropertiesGrammar", optional=True),
            ),
            # Create like syntax
            Sequence(
                "LIKE",
                Ref("TableReferenceSegment"),
                Ref("LocationGrammar", optional=True),
            ),
        ),
    )


@hive_dialect.segment()
class PrimitiveTypeSegment(BaseSegment):
    """Primitive data types."""

    type = "primitive_type"
    match_grammar = OneOf(
        "TINYINT",
        "SMALLINT",
        "INT",
        "BIGINT",
        "BOOLEAN",
        "FLOAT",
        Sequence("DOUBLE", Ref.keyword("PRECISION", optional=True)),
        "STRING",
        "BINARY",
        "TIMESTAMP",
        Sequence(
            "DECIMAL",
            Bracketed(
                Ref("NumericLiteralSegment"),
                Ref("CommaSegment"),
                Ref("NumericLiteralSegment"),
                optional=True,
            ),
        ),
        "DATE",
        "VARCHAR",
        "CHAR",
    )


@hive_dialect.segment(replace=True)
class DatatypeSegment(BaseSegment):
    """Data types."""

    type = "data_type"
    match_grammar = OneOf(
        Ref("PrimitiveTypeSegment"),
        Sequence("ARRAY", Bracketed(Ref("DatatypeSegment"), bracket_type="angle")),
        Sequence(
            "MAP",
            Bracketed(
                Ref("PrimitiveTypeSegment"),
                Ref("CommaSegment"),
                Ref("DatatypeSegment"),
                bracket_type="angle",
            ),
        ),
        Sequence(
            "STRUCT",
            Bracketed(
                Delimited(
                    Sequence(
                        Ref("NakedIdentifierSegment"),
                        Ref("ColonSegment"),
                        Ref("DatatypeSegment"),
                    ),
                ),
                bracket_type="angle",
            ),
        ),
        Sequence(
            "UNIONTYPE",
            Bracketed(Delimited(Ref("DatatypeSegment")), bracket_type="angle"),
        ),
    )


@hive_dialect.segment()
class SkewedByClauseSegment(BaseSegment):
    """`SKEWED BY` clause in a CREATE / ALTER statement."""

    type = "skewed_by_clause"
    match_grammar = Sequence(
        "SKEWED",
        "BY",
        Ref("BracketedColumnReferenceListGrammar"),
        "ON",
        Bracketed(
            Delimited(
                OneOf(
                    Ref("LiteralGrammar"), Bracketed(Delimited(Ref("LiteralGrammar")))
                )
            )
        ),
        Sequence("STORED", "AS", "DIRECTORIES", optional=True),
    )


@hive_dialect.segment()
class RowFormatClauseSegment(BaseSegment):
    """`ROW FORMAT` clause in a CREATE statement."""

    type = "row_format_clause"
    match_grammar = Sequence(
        "ROW",
        "FORMAT",
        OneOf(
            Sequence(
                "DELIMITED",
                Sequence(
                    "FIELDS",
                    Ref("TerminatedByGrammar"),
                    Sequence(
                        "ESCAPED", "BY", Ref("QuotedliteralSegment"), optional=True
                    ),
                    optional=True,
                ),
                Sequence(
                    "COLLECTION", "ITEMS", Ref("TerminatedByGrammar"), optional=True
                ),
                Sequence("MAP", "KEYS", Ref("TerminatedByGrammar"), optional=True),
                Sequence("LINES", Ref("TerminatedByGrammar"), optional=True),
                Sequence(
                    "NULL", "DEFINED", "AS", Ref("QuotedliteralSegment"), optional=True
                ),
            ),
            Sequence(
                "SERDE",
                Ref("QuotedLiteralSegment"),
                Ref("SerdePropertiesGrammar", optional=True),
            ),
        ),
    )
