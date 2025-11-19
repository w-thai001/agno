"""
Unified Query Builder

Provides a database-agnostic query builder interface.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union


class QueryType(Enum):
    """Types of database queries."""

    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE_TABLE = "CREATE_TABLE"
    DROP_TABLE = "DROP_TABLE"
    ALTER_TABLE = "ALTER_TABLE"


class JoinType(Enum):
    """Types of SQL joins."""

    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL OUTER JOIN"
    CROSS = "CROSS JOIN"


class Query:
    """
    Unified query builder for multiple database types.

    Supports both SQL (PostgreSQL, MySQL, SQLite) and NoSQL (MongoDB) databases.
    """

    def __init__(self, db_type: str):
        """
        Initialize query builder.

        Args:
            db_type: Type of database ('postgres', 'mysql', 'sqlite', 'mongodb')
        """
        self.db_type = db_type.lower()
        self.query_type: Optional[QueryType] = None
        self.table_name: Optional[str] = None
        self.collection_name: Optional[str] = None
        self.select_fields: List[str] = []
        self.where_conditions: List[Dict[str, Any]] = []
        self.join_clauses: List[Dict[str, Any]] = []
        self.order_by_clauses: List[Dict[str, str]] = []
        self.group_by_fields: List[str] = []
        self.having_conditions: List[Dict[str, Any]] = []
        self.limit_value: Optional[int] = None
        self.offset_value: Optional[int] = None
        self.insert_data: Optional[Dict[str, Any]] = None
        self.update_data: Optional[Dict[str, Any]] = None

    def select(self, *fields: str) -> "Query":
        """
        Add SELECT clause.

        Args:
            *fields: Fields to select (use '*' for all fields)

        Returns:
            Self for method chaining
        """
        self.query_type = QueryType.SELECT
        self.select_fields = list(fields) if fields else ["*"]
        return self

    def from_table(self, table: str) -> "Query":
        """
        Specify table/collection name.

        Args:
            table: Name of the table or collection

        Returns:
            Self for method chaining
        """
        if self.db_type == "mongodb":
            self.collection_name = table
        else:
            self.table_name = table
        return self

    def where(self, field: str, operator: str = "=", value: Any = None) -> "Query":
        """
        Add WHERE condition.

        Args:
            field: Field name
            operator: Comparison operator (=, !=, >, <, >=, <=, IN, LIKE, etc.)
            value: Value to compare against

        Returns:
            Self for method chaining
        """
        self.where_conditions.append({"field": field, "operator": operator, "value": value})
        return self

    def where_in(self, field: str, values: List[Any]) -> "Query":
        """
        Add WHERE IN condition.

        Args:
            field: Field name
            values: List of values

        Returns:
            Self for method chaining
        """
        return self.where(field, "IN", values)

    def join(self, table: str, on_condition: str, join_type: JoinType = JoinType.INNER) -> "Query":
        """
        Add JOIN clause (SQL only).

        Args:
            table: Table to join
            on_condition: Join condition (e.g., "users.id = posts.user_id")
            join_type: Type of join (default: INNER)

        Returns:
            Self for method chaining
        """
        self.join_clauses.append({"table": table, "on": on_condition, "type": join_type})
        return self

    def order_by(self, field: str, direction: str = "ASC") -> "Query":
        """
        Add ORDER BY clause.

        Args:
            field: Field to order by
            direction: 'ASC' or 'DESC' (default: ASC)

        Returns:
            Self for method chaining
        """
        self.order_by_clauses.append({"field": field, "direction": direction.upper()})
        return self

    def group_by(self, *fields: str) -> "Query":
        """
        Add GROUP BY clause.

        Args:
            *fields: Fields to group by

        Returns:
            Self for method chaining
        """
        self.group_by_fields.extend(fields)
        return self

    def having(self, field: str, operator: str, value: Any) -> "Query":
        """
        Add HAVING clause.

        Args:
            field: Field name
            operator: Comparison operator
            value: Value to compare against

        Returns:
            Self for method chaining
        """
        self.having_conditions.append({"field": field, "operator": operator, "value": value})
        return self

    def limit(self, count: int) -> "Query":
        """
        Add LIMIT clause.

        Args:
            count: Maximum number of results

        Returns:
            Self for method chaining
        """
        self.limit_value = count
        return self

    def offset(self, count: int) -> "Query":
        """
        Add OFFSET clause.

        Args:
            count: Number of results to skip

        Returns:
            Self for method chaining
        """
        self.offset_value = count
        return self

    def insert(self, data: Dict[str, Any]) -> "Query":
        """
        Create INSERT query.

        Args:
            data: Dictionary of field-value pairs to insert

        Returns:
            Self for method chaining
        """
        self.query_type = QueryType.INSERT
        self.insert_data = data
        return self

    def update(self, data: Dict[str, Any]) -> "Query":
        """
        Create UPDATE query.

        Args:
            data: Dictionary of field-value pairs to update

        Returns:
            Self for method chaining
        """
        self.query_type = QueryType.UPDATE
        self.update_data = data
        return self

    def delete(self) -> "Query":
        """
        Create DELETE query.

        Returns:
            Self for method chaining
        """
        self.query_type = QueryType.DELETE
        return self

    def build(self) -> Union[str, Dict[str, Any]]:
        """
        Build the final query.

        Returns:
            SQL string for SQL databases, or dict for MongoDB

        Raises:
            ValueError: If query is invalid
        """
        if self.db_type == "mongodb":
            return self._build_mongodb_query()
        else:
            return self._build_sql_query()

    def _build_sql_query(self) -> str:
        """Build SQL query string."""
        if self.query_type == QueryType.SELECT:
            return self._build_select()
        elif self.query_type == QueryType.INSERT:
            return self._build_insert()
        elif self.query_type == QueryType.UPDATE:
            return self._build_update()
        elif self.query_type == QueryType.DELETE:
            return self._build_delete()
        else:
            raise ValueError(f"Unsupported query type: {self.query_type}")

    def _build_select(self) -> str:
        """Build SELECT query."""
        fields = ", ".join(self.select_fields)
        query = f"SELECT {fields} FROM {self.table_name}"

        # Add JOINs
        for join in self.join_clauses:
            query += f" {join['type'].value} {join['table']} ON {join['on']}"

        # Add WHERE
        if self.where_conditions:
            where_parts = []
            for cond in self.where_conditions:
                if cond["operator"] == "IN":
                    values = ", ".join([self._format_value(v) for v in cond["value"]])
                    where_parts.append(f"{cond['field']} IN ({values})")
                else:
                    where_parts.append(f"{cond['field']} {cond['operator']} {self._format_value(cond['value'])}")
            query += " WHERE " + " AND ".join(where_parts)

        # Add GROUP BY
        if self.group_by_fields:
            query += " GROUP BY " + ", ".join(self.group_by_fields)

        # Add HAVING
        if self.having_conditions:
            having_parts = [
                f"{cond['field']} {cond['operator']} {self._format_value(cond['value'])}"
                for cond in self.having_conditions
            ]
            query += " HAVING " + " AND ".join(having_parts)

        # Add ORDER BY
        if self.order_by_clauses:
            order_parts = [f"{clause['field']} {clause['direction']}" for clause in self.order_by_clauses]
            query += " ORDER BY " + ", ".join(order_parts)

        # Add LIMIT/OFFSET
        if self.limit_value is not None:
            query += f" LIMIT {self.limit_value}"
        if self.offset_value is not None:
            query += f" OFFSET {self.offset_value}"

        return query

    def _build_insert(self) -> str:
        """Build INSERT query."""
        if not self.insert_data:
            raise ValueError("No data provided for INSERT query")

        fields = ", ".join(self.insert_data.keys())
        values = ", ".join([self._format_value(v) for v in self.insert_data.values()])

        if self.db_type == "postgres":
            return f"INSERT INTO {self.table_name} ({fields}) VALUES ({values}) RETURNING *"
        else:
            return f"INSERT INTO {self.table_name} ({fields}) VALUES ({values})"

    def _build_update(self) -> str:
        """Build UPDATE query."""
        if not self.update_data:
            raise ValueError("No data provided for UPDATE query")

        set_parts = [f"{field} = {self._format_value(value)}" for field, value in self.update_data.items()]
        query = f"UPDATE {self.table_name} SET {', '.join(set_parts)}"

        # Add WHERE
        if self.where_conditions:
            where_parts = [
                f"{cond['field']} {cond['operator']} {self._format_value(cond['value'])}"
                for cond in self.where_conditions
            ]
            query += " WHERE " + " AND ".join(where_parts)

        return query

    def _build_delete(self) -> str:
        """Build DELETE query."""
        query = f"DELETE FROM {self.table_name}"

        # Add WHERE
        if self.where_conditions:
            where_parts = [
                f"{cond['field']} {cond['operator']} {self._format_value(cond['value'])}"
                for cond in self.where_conditions
            ]
            query += " WHERE " + " AND ".join(where_parts)

        return query

    def _build_mongodb_query(self) -> Dict[str, Any]:
        """Build MongoDB query document."""
        query_doc: Dict[str, Any] = {"collection": self.collection_name}

        if self.query_type == QueryType.SELECT:
            # Build filter
            filter_doc = {}
            for cond in self.where_conditions:
                if cond["operator"] == "=":
                    filter_doc[cond["field"]] = cond["value"]
                elif cond["operator"] == "IN":
                    filter_doc[cond["field"]] = {"$in": cond["value"]}
                elif cond["operator"] == ">":
                    filter_doc[cond["field"]] = {"$gt": cond["value"]}
                elif cond["operator"] == ">=":
                    filter_doc[cond["field"]] = {"$gte": cond["value"]}
                elif cond["operator"] == "<":
                    filter_doc[cond["field"]] = {"$lt": cond["value"]}
                elif cond["operator"] == "<=":
                    filter_doc[cond["field"]] = {"$lte": cond["value"]}
                elif cond["operator"] == "!=":
                    filter_doc[cond["field"]] = {"$ne": cond["value"]}

            query_doc["filter"] = filter_doc
            query_doc["operation"] = "find"

            # Add projection (fields to select)
            if self.select_fields and "*" not in self.select_fields:
                query_doc["projection"] = {field: 1 for field in self.select_fields}

            # Add sort
            if self.order_by_clauses:
                query_doc["sort"] = [(clause["field"], 1 if clause["direction"] == "ASC" else -1) for clause in self.order_by_clauses]

            # Add limit/skip
            if self.limit_value:
                query_doc["limit"] = self.limit_value
            if self.offset_value:
                query_doc["skip"] = self.offset_value

        elif self.query_type == QueryType.INSERT:
            query_doc["operation"] = "insert_one"
            query_doc["document"] = self.insert_data

        elif self.query_type == QueryType.UPDATE:
            query_doc["operation"] = "update_many"
            # Build filter
            filter_doc = {}
            for cond in self.where_conditions:
                filter_doc[cond["field"]] = cond["value"]
            query_doc["filter"] = filter_doc
            query_doc["update"] = {"$set": self.update_data}

        elif self.query_type == QueryType.DELETE:
            query_doc["operation"] = "delete_many"
            # Build filter
            filter_doc = {}
            for cond in self.where_conditions:
                filter_doc[cond["field"]] = cond["value"]
            query_doc["filter"] = filter_doc

        return query_doc

    def _format_value(self, value: Any) -> str:
        """Format value for SQL query."""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            # Escape single quotes
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            # For other types, convert to string and quote
            return f"'{str(value)}'"
