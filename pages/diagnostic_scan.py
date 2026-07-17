import streamlit as st

from modules.database_functions import get_photos, save_photo
from modules.image_handler import process_image_upload


def render_diagnostic_scan():
    st.title("🧪 Diagnostic Scan")
    st.caption("Capture scan details, fault codes, and supporting files.")
    inspection_id = st.session_state.get("inspection_id")
    if not inspection_id:
        st.info("Start a new inspection first.")
        return

    obd_name = st.text_input("OBD Scanner Name")
    fault_codes = st.text_area("Fault Codes")
    engine_light = st.selectbox("Engine Light", ["Off", "On", "Intermittent"])
    abs_status = st.selectbox("ABS", ["Normal", "Fault", "Not Tested"])
    airbag_status = st.selectbox("Airbag", ["Normal", "Fault", "Not Tested"])
    scan_pdf = st.file_uploader("Upload Scan PDF", type=["pdf"])
    screenshot = st.file_uploader("Upload Screenshot", type=["jpg", "jpeg", "png", "webp"])

    if st.button("Save Diagnostic Scan"):
        if screenshot:
            saved_path = process_image_upload(screenshot, inspection_id, "Diagnostic Scan", "Screenshot")
            if saved_path:
                save_photo(inspection_id, "Diagnostic Scan", saved_path, caption="Screenshot")
        if scan_pdf:
            save_photo(inspection_id, "Diagnostic Scan", f"uploads/{scan_pdf.name}", caption="Scan PDF")
        st.success("Diagnostic scan details saved")

    st.markdown("---")
    st.subheader("Saved evidence")
    photos = get_photos(inspection_id, category="Diagnostic Scan")
    if photos:
        for photo in photos:
            st.image(photo["file_path"], width=220)
    else:
        st.info("No diagnostic scan evidence yet")
