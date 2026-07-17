import streamlit as st

from modules.database_functions import get_inspection_items, get_photos, update_inspection_summary, delete_inspection_item


def render_inspection_summary():
    st.title("🧾 Inspection Summary")
    st.caption("Review the session findings, photos, and save a brief summary.")
    inspection_id = st.session_state.get("inspection_id")
    if not inspection_id:
        st.info("Start a new inspection first.")
        return

    items = get_inspection_items(inspection_id)
    photos = get_photos(inspection_id)

    col1, col2 = st.columns(2)
    col1.metric("Total Findings", len(items))
    col2.metric("Total Photos", len(photos))

    st.markdown("---")
    st.subheader("Session Summary")
    if items:
        grouped = {}
        for it in items:
            cat = it.get('category', 'Uncategorized')
            grouped.setdefault(cat, []).append(it)

        for cat, cat_items in grouped.items():
            st.write(f"**{cat}**")
            for it in cat_items:
                cols = st.columns([5, 1])
                with cols[0]:
                    st.write(f"- {it.get('part_name')} — {it.get('remarks', '')}")
                with cols[1]:
                    if st.button("Delete", key=f"delete_summary_finding_{it['item_id']}"):
                        if delete_inspection_item(it["item_id"]):
                            st.success("Finding deleted.")
                            st.rerun()
                        else:
                            st.error("Unable to delete finding.")
    else:
        st.info("No findings saved for this inspection yet.")

    st.markdown("---")
    st.subheader("Inspection Photos")
    if photos:
        for photo in photos:
            st.image(photo['file_path'], width=220)

    if st.button("Save Summary"):
        summary_text = "Session summary saved."
        update_inspection_summary(
            inspection_id,
            0.0,
            'Pending',
            0.0,
            summary_text,
        )
        st.success("Summary saved")
