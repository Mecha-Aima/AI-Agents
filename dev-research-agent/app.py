import streamlit as st
from src.workflow import Workflow
from src.models import CompanyInfo

st.set_page_config(page_title="Dev Tools Research Assistant", page_icon="🛠️")

st.title("Dev Tools Research Assistant")

if "workflow" not in st.session_state:
    st.session_state.workflow = Workflow(status_callback=st.info)
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What dev tools are you looking for?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = st.session_state.workflow.run(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response.analysis})
                st.markdown(response.analysis)

                if response.companies:
                    st.write("Here are some of the tools I found:")
                    for company in response.companies:
                        st.write(f"### {company.name}")
                        st.write(f"**Website:** {company.website}")
                        st.write(f"**Pricing:** {company.pricing_model}")
                        st.write(f"**Open Source:** {'Yes' if company.is_open_source else 'No'}")
                        st.write(f"**Tech Stack:** {', '.join(company.tech_stack)}")
                        st.write(f"**Integrations:** {', '.join(company.integration_capabilities)}")
                        st.write(f"**Description:** {company.description}")
                        st.divider()
                else:
                    st.warning("⚠️ No tools were found for your query. This might be due to rate limiting or insufficient search results. Please try again in a few moments or rephrase your query.")
            except Exception as e:
                error_msg = f"❌ An error occurred while processing your request: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

if st.button("New Conversation"):
    st.session_state.messages = []
    st.rerun()
