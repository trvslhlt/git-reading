"""Author Network visualization - explore author influences and literary connections."""

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import streamlit as st

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from load.db import get_adapter  # noqa: E402


@st.cache_data
def load_author_network():
    """Load author influence network from database.

    Returns:
        dict with:
            - authors: list of author dicts
            - influences: list of influence relationship dicts
            - stats: network statistics
    """
    adapter = get_adapter()

    try:
        adapter.connect()
        # Get all authors with Wikidata IDs
        authors_query = """
            SELECT
                id,
                name,
                first_name,
                last_name,
                wikidata_id,
                birth_year,
                death_year,
                birth_place,
                death_place,
                nationality
            FROM authors
            WHERE wikidata_id IS NOT NULL
            ORDER BY name
        """
        authors = adapter.fetchall(authors_query)

        # Get influence relationships
        influences_query = """
            SELECT
                ai.influencer_id,
                ai.influenced_id,
                a1.name as influencer_name,
                a2.name as influenced_name
            FROM author_influences ai
            JOIN authors a1 ON ai.influencer_id = a1.id
            JOIN authors a2 ON ai.influenced_id = a2.id
        """
        influences = adapter.fetchall(influences_query)

        # Calculate statistics
        # author_ids = {a["id"] for a in authors}

        # Count influences per author
        influenced_by_count = defaultdict(int)
        influenced_count = defaultdict(int)

        for inf in influences:
            influenced_by_count[inf["influenced_id"]] += 1
            influenced_count[inf["influencer_id"]] += 1

        # Find most influential (influenced the most others)
        most_influential = []
        for author in authors:
            count = influenced_count.get(author["id"], 0)
            if count > 0:
                most_influential.append((author["name"], count))
        most_influential.sort(key=lambda x: x[1], reverse=True)

        # Find most influenced (influenced by the most others)
        most_influenced = []
        for author in authors:
            count = influenced_by_count.get(author["id"], 0)
            if count > 0:
                most_influenced.append((author["name"], count))
        most_influenced.sort(key=lambda x: x[1], reverse=True)

        stats = {
            "total_authors": len(authors),
            "total_influences": len(influences),
            "authors_with_influences": len({inf["influencer_id"] for inf in influences}),
            "authors_influenced": len({inf["influenced_id"] for inf in influences}),
            "most_influential": most_influential[:10],
            "most_influenced": most_influenced[:10],
        }

        return {
            "authors": authors,
            "influences": influences,
            "stats": stats,
        }

    except Exception as e:
        st.error(f"Error loading author network: {e}")
        return {
            "authors": [],
            "influences": [],
            "stats": {},
        }
    finally:
        adapter.close()


def build_network_data(authors, influences, selected_authors=None):
    """Build network data for visualization.

    Args:
        authors: List of author dicts
        influences: List of influence relationship dicts
        selected_authors: Optional list of author IDs to filter to

    Returns:
        dict with nodes and edges for network graph
    """
    # Filter to selected authors if specified
    if selected_authors:
        author_ids = set(selected_authors)
        # Also include authors they influenced or were influenced by
        for inf in influences:
            if inf["influencer_id"] in selected_authors:
                author_ids.add(inf["influenced_id"])
            if inf["influenced_id"] in selected_authors:
                author_ids.add(inf["influencer_id"])

        authors = [a for a in authors if a["id"] in author_ids]
        influences = [
            i
            for i in influences
            if i["influencer_id"] in author_ids and i["influenced_id"] in author_ids
        ]

    # Build nodes
    nodes = []
    for author in authors:
        birth = author.get("birth_year") or "?"
        death = author.get("death_year") or "?"
        nodes.append(
            {
                "id": author["id"],
                "label": author["name"],
                "title": f"{author['name']}\n{birth} - {death}",
            }
        )

    # Build edges
    edges = []
    for inf in influences:
        edges.append(
            {
                "from": inf["influencer_id"],
                "to": inf["influenced_id"],
                "title": f"{inf['influencer_name']} → {inf['influenced_name']}",
            }
        )

    return {"nodes": nodes, "edges": edges}


def render_network_graph(network_data):
    """Render network graph using Streamlit's native graph capabilities.

    For now, this creates a simple text-based representation.
    TODO: Integrate with pyvis or networkx for interactive visualization.
    """
    nodes = network_data["nodes"]
    edges = network_data["edges"]

    if not nodes:
        st.info("No authors to display in network")
        return

    if not edges:
        st.info("No influence relationships found for these authors")
        return

    st.markdown(f"**Network:** {len(nodes)} authors, {len(edges)} influence relationships")

    # Show influence relationships as a table
    st.subheader("Influence Relationships")

    # Create a lookup dict for faster access
    node_lookup = {n["id"]: n for n in nodes}

    relationships = []
    for edge in edges:
        # Skip edges where nodes don't exist (shouldn't happen, but be safe)
        if edge["from"] not in node_lookup or edge["to"] not in node_lookup:
            continue

        influencer = node_lookup[edge["from"]]
        influenced = node_lookup[edge["to"]]
        relationships.append(
            {
                "Influencer": influencer["label"],
                "→": "→",
                "Influenced": influenced["label"],
            }
        )

    if relationships:
        df = pd.DataFrame(relationships)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("No relationships to display")


def main():
    st.title("🕸️ Author Network")
    st.markdown("*Explore author influences and literary connections*")

    # Load network data
    with st.spinner("Loading author network..."):
        data = load_author_network()

    authors = data["authors"]
    influences = data["influences"]
    stats = data["stats"]

    if not authors:
        st.warning(
            "No authors with Wikidata enrichment found. "
            "Run enrichment first:\n\n"
            "```bash\nmake run-enrich ARGS='--sources wikidata --entity-type authors'\n```"
        )
        return

    # Overview statistics
    st.header("Network Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Authors", stats["total_authors"])

    with col2:
        st.metric("Influence Relationships", stats["total_influences"])

    with col3:
        st.metric("Authors Who Influenced Others", stats["authors_with_influences"])

    with col4:
        st.metric("Authors Who Were Influenced", stats["authors_influenced"])

    # Most influential authors
    if stats.get("most_influential"):
        st.subheader("Most Influential Authors")
        st.markdown("*Authors who influenced the most others*")

        influential_data = []
        for name, count in stats["most_influential"]:
            influential_data.append(
                {
                    "Author": name,
                    "Influenced": f"{count} authors",
                }
            )

        df = pd.DataFrame(influential_data)
        st.dataframe(df, hide_index=True, use_container_width=True)

    # Most influenced authors
    if stats.get("most_influenced"):
        st.subheader("Most Influenced Authors")
        st.markdown("*Authors influenced by the most others*")

        influenced_data = []
        for name, count in stats["most_influenced"]:
            influenced_data.append(
                {
                    "Author": name,
                    "Influenced By": f"{count} authors",
                }
            )

        df = pd.DataFrame(influenced_data)
        st.dataframe(df, hide_index=True, use_container_width=True)

    # Filter controls
    st.header("Explore Network")

    # Author selection
    author_names = {a["id"]: a["name"] for a in authors}
    selected = st.multiselect(
        "Select authors to explore their influence network",
        options=list(author_names.keys()),
        format_func=lambda x: author_names[x],
        help="Select one or more authors to see their influence connections",
    )

    if selected:
        # Build filtered network
        network_data = build_network_data(authors, influences, selected)

        # Render network
        render_network_graph(network_data)

        # Show selected author details
        st.subheader("Author Details")

        for author_id in selected:
            author = next(a for a in authors if a["id"] == author_id)

            with st.expander(f"**{author['name']}**"):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Biographical Info:**")
                    if author.get("birth_year"):
                        st.markdown(f"- Born: {author['birth_year']}")
                    if author.get("death_year"):
                        st.markdown(f"- Died: {author['death_year']}")
                    if author.get("birth_place"):
                        st.markdown(f"- Birth Place: {author['birth_place']}")
                    if author.get("nationality"):
                        st.markdown(f"- Nationality: {author['nationality']}")

                with col2:
                    # Find influences
                    influenced_by = [
                        i["influencer_name"] for i in influences if i["influenced_id"] == author_id
                    ]
                    influenced = [
                        i["influenced_name"] for i in influences if i["influencer_id"] == author_id
                    ]

                    st.markdown("**Influence Network:**")
                    if influenced_by:
                        st.markdown(f"- Influenced by: {', '.join(influenced_by)}")
                    if influenced:
                        st.markdown(f"- Influenced: {', '.join(influenced)}")

                    if not influenced_by and not influenced:
                        st.markdown("*No influence data available*")

    else:
        st.info("👆 Select authors above to explore their influence network")

    # Full network view
    st.header("Full Network")

    if st.checkbox("Show full network (may be large)", value=False):
        network_data = build_network_data(authors, influences)
        render_network_graph(network_data)


if __name__ == "__main__":
    main()
