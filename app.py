
import json

import streamlit as st
from document_processor import process_document, process_document_ai

st.set_page_config(
    page_title="Document Understanding Assistant",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Document Understanding Assistant")
st.caption("Arrowstack AI/ML Internship — Project 2")

st.write(
    "Upload a sample business PDF or TXT file to extract key information, "
    "generate a summary, and validate structured output."
)

uploaded = st.file_uploader(
    "Choose a PDF or TXT document",
    type=["pdf", "txt"],
)

if uploaded:
    content = uploaded.getvalue()

    baseline_tab, ai_tab, comparison_tab = st.tabs(
        ["Baseline Results", "Local AI Results", "Comparison"]
    )

    # Baseline: rule-based extraction and simple summarization.
    with baseline_tab:
        st.subheader("Baseline processing")

        try:
            baseline = process_document(uploaded.name, content)

            st.subheader("Document summary")
            st.write(baseline["summary"])

            st.subheader("Extracted entities")
            st.json(baseline["entities"])

            st.subheader("Structured output")
            st.json(baseline["structured_data"])

            if baseline["validation"]["valid"]:
                st.success("JSON schema validation passed")
            else:
                st.error("JSON schema validation failed")
                st.write(baseline["validation"]["errors"])

            st.download_button(
                "Download baseline JSON",
                data=json.dumps(baseline, indent=2),
                file_name="baseline_analysis.json",
                mime="application/json",
                key="download_baseline",
            )

        except Exception as exc:
            baseline = None
            st.error(f"Baseline processing failed: {exc}")

    # AI: local Ollama model.
    with ai_tab:
        st.subheader("Local AI processing")
        st.caption("Model: llama3.2:latest running through Ollama")

        if st.button("Run local AI analysis", type="primary"):
            with st.spinner("Analyzing document with local Ollama model..."):
                try:
                    st.session_state["ai_result"] = process_document_ai(
                        uploaded.name,
                        content,
                    )
                    st.session_state["ai_filename"] = uploaded.name
                    st.session_state["ai_content"] = content
                    st.success("AI analysis completed.")

                except Exception as exc:
                    st.error(f"AI processing failed: {exc}")

        ai_result = st.session_state.get("ai_result")

        if (
            ai_result
            and st.session_state.get("ai_filename") == uploaded.name
            and st.session_state.get("ai_content") == content
        ):
            st.subheader("AI-generated summary")
            st.write(ai_result["summary"])

            st.subheader("AI-extracted entities")
            st.json(ai_result["entities"])

            st.subheader("AI structured output")
            st.json(ai_result["structured_data"])

            if ai_result["validation"]["valid"]:
                st.success("AI JSON schema validation passed")
            else:
                st.error("AI JSON schema validation failed")
                st.write(ai_result["validation"]["errors"])

            st.download_button(
                "Download AI JSON",
                data=json.dumps(ai_result, indent=2),
                file_name="ai_analysis.json",
                mime="application/json",
                key="download_ai",
            )

    # Compare results from both approaches.
    with comparison_tab:
        st.subheader("Baseline versus AI")

        ai_result = st.session_state.get("ai_result")

        if (
            ai_result
            and st.session_state.get("ai_filename") == uploaded.name
            and st.session_state.get("ai_content") == content
        ):
            if baseline is not None:
                st.markdown("**Summary comparison**")

                left, right = st.columns(2)

                with left:
                    st.markdown("Baseline")
                    st.write(baseline["summary"])

                with right:
                    st.markdown("Local AI")
                    st.write(ai_result["summary"])

                st.markdown("**Entity comparison**")

                left, right = st.columns(2)

                with left:
                    st.markdown("Baseline entities")
                    st.json(baseline["entities"])

                with right:
                    st.markdown("AI entities")
                    st.json(ai_result["entities"])

                st.markdown("**Schema validation**")

                st.write({
                    "baseline_valid": baseline["validation"]["valid"],
                    "ai_valid": ai_result["validation"]["valid"],
                })

                st.caption(
                    "Schema validity checks output structure, not factual "
                    "accuracy. Review extracted values against the source."
                )
        else:
            st.info(
                "Click 'Run local AI analysis' in the Local AI Results tab "
                "to generate results for comparison."
            )

    st.divider()

    st.subheader("Source text")
    st.caption("Verify extracted information against the original document.")

    try:
        source = process_document(uploaded.name, content)
        st.text_area(
            "Extracted document text",
            source["text"],
            height=180,
        )
    except Exception as exc:
        st.warning(f"Could not display source text: {exc}")

    st.warning(
        "Human review required: extraction and summaries may contain errors. "
        "Verify important information against the source document."
    )
