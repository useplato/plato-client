#!/usr/bin/env python3
"""
Streamlit UI to configure ignore_tables and ignore_columns.

Usage: uv run streamlit run configure_ignore_tables_ui.py
"""
import streamlit as st
import json


def connect_db(db_type, host, port, user, password, database):
    if db_type == "postgresql" or port == 5432:
        import psycopg2
        return psycopg2.connect(host=host, port=port, user=user, password=password, database=database), "postgresql"
    else:
        import pymysql
        return pymysql.connect(host=host, port=port, user=user, password=password, database=database), "mysql"


def load_all_data(conn, db_type):
    cursor = conn.cursor()

    if db_type == "postgresql":
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name")
    else:
        cursor.execute("SHOW TABLES")

    tables = [row[0] for row in cursor.fetchall()]
    all_data = {}

    for table in tables:
        quote = '"' if db_type == "postgresql" else "`"

        # Columns
        if db_type == "postgresql":
            cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}' AND table_schema = 'public' ORDER BY ordinal_position")
            cols = [{'name': r[0], 'type': r[1]} for r in cursor.fetchall()]
        else:
            cursor.execute(f"DESCRIBE `{table}`")
            cols = [{'name': r[0], 'type': str(r[1])} for r in cursor.fetchall()]

        # Count
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {quote}{table}{quote}')
            count = cursor.fetchone()[0]
        except:
            count = 0

        # Example values per column
        col_examples = {}
        for col in cols[:20]:  # Limit to first 20 columns for performance
            try:
                cursor.execute(f'SELECT DISTINCT {quote}{col["name"]}{quote} FROM {quote}{table}{quote} WHERE {quote}{col["name"]}{quote} IS NOT NULL LIMIT 3')
                values = [str(row[0])[:40] for row in cursor.fetchall()]
                col_examples[col['name']] = values
            except:
                col_examples[col['name']] = []

        all_data[table] = {'columns': cols, 'count': count, 'col_examples': col_examples}

    return tables, all_data


def main():
    st.set_page_config(page_title="Ignore Tables", layout="wide")
    st.title("🔍 Ignore Tables & Columns")

    # Initialize ALL state first
    if 'ignore_tables' not in st.session_state:
        st.session_state.ignore_tables = set()
    if 'ignore_cols_global' not in st.session_state:
        st.session_state.ignore_cols_global = set()
    if 'ignore_cols_per_table' not in st.session_state:
        st.session_state.ignore_cols_per_table = {}
    if 'show_columns' not in st.session_state:
        st.session_state.show_columns = False

    # Sidebar - use query params to persist connection
    st.sidebar.header("📡 Connection")

    qp = st.query_params

    host = st.sidebar.text_input("Host", qp.get("host", "127.0.0.1"))
    port = st.sidebar.number_input("Port", min_value=1, max_value=65535, value=int(qp.get("port", "3306")))
    user = st.sidebar.text_input("User", qp.get("user", "photoprism"))
    password = st.sidebar.text_input("Password", qp.get("password", "photoprism"), type="password")
    database = st.sidebar.text_input("Database", qp.get("database", "photoprism"))

    # Update query params
    st.query_params.update({"host": host, "port": str(port), "user": user, "password": password, "database": database})

    if st.sidebar.button("🔌 Connect & Load"):
        with st.spinner("Loading..."):
            try:
                conn, db_type = connect_db("postgresql" if port == 5432 else "mysql", host, port, user, password, database)
                tables, all_data = load_all_data(conn, db_type)
                st.session_state.tables = tables
                st.session_state.all_data = all_data
                st.sidebar.success(f"✅ {len(tables)} tables")
            except Exception as e:
                st.sidebar.error(f"❌ {e}")
                import traceback
                st.sidebar.code(traceback.format_exc())
                return

    if 'tables' not in st.session_state:
        st.info("👈 Connect")
        return

    tables = st.session_state.tables
    all_data = st.session_state.all_data

    st.sidebar.write(f"🚫 {len(st.session_state.ignore_tables)} tables")
    st.sidebar.write(f"🌐 {len(st.session_state.ignore_cols_global)} global")

    # Global filters
    st.write("### 🌐 Global Column Filters (ignored in ALL tables)")

    col1, col2 = st.columns([3, 1])
    with col1:
        new_global = st.text_input("Add column name:", placeholder="e.g., updated_at, created_at, modified_by", key="add_global")
    with col2:
        st.write("")  # Spacing
        if st.button("➕ Add", key="add_global_btn") and new_global:
            st.session_state.ignore_cols_global.add(new_global)

    if st.session_state.ignore_cols_global:
        st.write("**Currently ignored globally:**")
        cols_display = st.columns(4)
        for i, col in enumerate(sorted(st.session_state.ignore_cols_global)):
            with cols_display[i % 4]:
                if st.button(f"❌ {col}", key=f"rm_global_{col}", help="Click to remove"):
                    st.session_state.ignore_cols_global.discard(col)
    else:
        st.caption("No global column filters set")

    st.write("---")

    # Tables section
    col1, col2 = st.columns([4, 1])
    with col1:
        search = st.text_input("🔍 Search", "")
    with col2:
        show_cols = st.toggle("Show Columns", value=st.session_state.show_columns)
        st.session_state.show_columns = show_cols

    filtered = [t for t in tables if search.lower() in t.lower()] if search else tables

    st.write(f"### Tables ({len(filtered)})")

    # Display tables
    for table in filtered:
        is_ignored = table in st.session_state.ignore_tables
        data = all_data[table]

        # Table header with expand/collapse
        name = f"~~{table}~~" if is_ignored else table
        icon = "🚫" if is_ignored else "📋"

        # Expand if show_columns is on
        with st.expander(f"{icon} {name} — {data['count']} rows", expanded=st.session_state.show_columns):
            # Ignore table checkbox
            ign = st.checkbox("🚫 Ignore entire table", value=is_ignored, key=f"t_{table}")
            if ign:
                st.session_state.ignore_tables.add(table)
            else:
                st.session_state.ignore_tables.discard(table)

            # Show columns if not ignored
            if not ign:
                if table not in st.session_state.ignore_cols_per_table:
                    st.session_state.ignore_cols_per_table[table] = set()

                # Column header
                st.markdown("**Columns:**")
                h1, h2, h3, h4 = st.columns([0.5, 2, 1.5, 4], gap="small")
                h1.caption("Ign")
                h2.caption("Name")
                h3.caption("Type")
                h4.caption("Examples")

                for col in data['columns']:
                    col_name = col['name']
                    is_global = col_name in st.session_state.ignore_cols_global
                    is_local = col_name in st.session_state.ignore_cols_per_table[table]

                    examples = data['col_examples'].get(col_name, [])
                    ex_str = ', '.join(examples)

                    c1, c2, c3, c4 = st.columns([0.5, 2, 1.5, 4], gap="small")
                    with c1:
                        if is_global:
                            st.checkbox("", True, disabled=True, key=f"c_dis_{table}_{col_name}", label_visibility="collapsed", help="Globally ignored")
                        else:
                            chk = st.checkbox("", is_local, key=f"c_{table}_{col_name}", label_visibility="collapsed", help="Check to ignore this column")
                            if chk:
                                st.session_state.ignore_cols_per_table[table].add(col_name)
                            else:
                                st.session_state.ignore_cols_per_table[table].discard(col_name)

                    with c2:
                        name_display = f"~~{col_name}~~" if is_global or is_local else col_name
                        st.text(name_display)
                    with c3:
                        st.caption(col['type'][:25])
                    with c4:
                        ex_display = f"~~{ex_str[:80]}~~" if is_global or is_local else ex_str[:80]
                        st.caption(ex_display)

    # Output
    st.write("---")
    st.write("### 📝 Config")

    config = "audit_ignore_tables=[\n"

    # Add fully ignored tables as strings
    for t in sorted(st.session_state.ignore_tables):
        config += f'    "{t}",\n'

    # Add tables with column-level ignores as dicts
    for table, cols in sorted(st.session_state.ignore_cols_per_table.items()):
        if cols and table not in st.session_state.ignore_tables:
            config += f"    {{'table': '{table}', 'columns': {json.dumps(sorted(list(cols)))}}},\n"

    config += "]\n"

    if st.session_state.ignore_cols_global:
        config += "\n# Global column filters (apply to ALL tables):\n"
        config += "# These should be added to ignore_columns with '*' key if needed\n"
        config += f"# ignore_columns = {{'*': {json.dumps(sorted(list(st.session_state.ignore_cols_global)))}}}\n"

    if config.count('\n') > 2:
        st.code(config, language="python")
    else:
        st.info("Mark items to generate config")


if __name__ == "__main__":
    main()
