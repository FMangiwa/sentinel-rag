"""
app.py
Constrained Centered Login UI with Password Eye Toggle, Logout, Benchmark Tab, 
and Fixed Input Scrollbars.
"""

import json
import gradio as gr

from config import cfg
from ingest import MultiTenantIndexer
from core.security import SecurityContext
from core.retriever import HybridRetriever
from core.agent import AgenticRAGPipeline
from eval.evaluator import RAGSuiteEvaluator
from core.auth import verify_credentials

# Initialize core services
indexer = MultiTenantIndexer()
retriever = HybridRetriever(indexer)
agent_pipeline = AgenticRAGPipeline(retriever)
evaluator = RAGSuiteEvaluator(agent_pipeline)


def login_handler(username, password):
    """Processes user login attempt and toggles visibility of app views."""
    auth_result = verify_credentials(username, password)

    if auth_result["authenticated"]:
        session_data = {
            "username": auth_result["username"],
            "tenant_id": auth_result["tenant_id"],
            "role": auth_result["role"],
        }
        user_info_text = f"Logged in as: **{auth_result['username']}** ({auth_result['role'].upper()} @ {auth_result['tenant_id']})"

        return (
            gr.update(visible=False),
            gr.update(visible=True),
            session_data,
            "",
            user_info_text,
            "",
            "",
        )
    else:
        return (
            gr.update(visible=True),
            gr.update(visible=False),
            {},
            auth_result["error"],
            "",
            username,
            password,
        )


def logout_handler():
    """Resets session state and returns to the login screen."""
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        {},
        "",
        "",
        "",
        "",
        [],
        "{}",
        "",
        "{}",
    )


def chat_response(message, history, session_data):
    """Handles chat input using session state."""
    if not message.strip():
        return "", history, "{}"

    tenant_id = session_data.get("tenant_id", "insureLLM")
    user_role = session_data.get("role", "guest")

    sec_ctx = SecurityContext(tenant_id=tenant_id, user_role=user_role)
    output = agent_pipeline.run(message, sec_ctx)

    answer = output["answer"]
    trace_json = json.dumps(output["trace"], indent=2)

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})

    return "", history, trace_json


def run_eval_benchmark(session_data):
    """Executes evaluation benchmark using current session context."""
    user_role = session_data.get("role", "guest")

    # Explicit RBAC Gate: Only admin can execute benchmarks
    if user_role.lower() != "admin":
        warning_msg = f"⚠️ **Access Denied**: Role `{user_role}` is not authorized to run system benchmarks. Administrator privileges required."
        return warning_msg, json.dumps({"status": "403_Forbidden", "role": user_role}, indent=2)

    test_cases = [
        {
            "query": "How many employees does Insurellm have?",
            "expected_sources": ["overview.md"],
            "role": user_role,
        },
        {
            "query": "What products does Insurellm offer?",
            "expected_sources": ["overview.md"],
            "role": user_role,
        },
        {
            "query": "What is Bizllm?",
            "expected_sources": ["Bizllm.md"],
            "role": user_role,
        },
        {
            "query": "What are the pricing tiers for Bizllm?",
            "expected_sources": ["Bizllm.md"],
            "role": user_role,
        },
        {
            "query": "What is the history of Insurellm?",
            "expected_sources": ["about.md"],
            "role": user_role,
        },
    ]

    results = evaluator.run_benchmark(test_cases)
    summary_md = f"### 📊 Benchmark Score: {results['summary']['mean_faithfulness']} / 1.0"
    return summary_md, json.dumps(results["details"], indent=2)


def toggle_password_visibility(is_secret):
    """Switches password input between hidden and visible states."""
    if is_secret:
        return gr.update(type="text"), "🙈", False
    return gr.update(type="password"), "👁️", True


# Custom CSS to handle centering, compact logout button, and remove input scrollbars
CSS = """
.login-card {
    max-width: 420px;
    margin: 60px auto;
    padding: 30px;
    border-radius: 12px;
    border: 1px solid var(--border-color-primary);
    background: var(--background-fill-primary);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* Remove scrollbars from single-line text inputs */
.no-scroll input, 
.no-scroll textarea {
    overflow: hidden !important;
    resize: none !important;
}

/* Enable vertical scrolling for chat input box */
.scroll-input textarea {
    overflow-y: auto !important;
    resize: vertical !important;
    max-height: 120px !important;
}

/* Compact Logout Button */
.logout-btn {
    max-width: 100px !important;
    min-width: 80px !important;
    height: 36px !important;
    font-size: 0.85rem !important;
    padding: 2px 8px !important;
    margin-top: 4px;
}
"""

with gr.Blocks(title="Enterprise Agentic RAG Platform") as demo:
    session_state = gr.State(value={})
    pwd_is_secret = gr.State(value=True)

    # =========================================================================
    # VIEW 1: CONSTRAINED CENTERED LOGIN CARD
    # =========================================================================
    with gr.Column(visible=True) as login_view:
        with gr.Row():
            gr.Column(scale=1)
            with gr.Column(scale=2, elem_classes=["login-card"]):
                gr.Markdown("### 🛡️ Enterprise Login", elem_classes=["text-center"])

                username_box = gr.Textbox(
                    label="Username",
                    placeholder="Enter username (e.g. alice, bob)",
                    autofocus=True,
                    lines=1,
                    max_lines=1,
                    elem_classes=["no-scroll"],
                )

                with gr.Row():
                    password_box = gr.Textbox(
                        label="Password",
                        type="password",
                        placeholder="Enter password",
                        scale=4,
                        lines=1,
                        max_lines=1,
                        elem_classes=["no-scroll"],
                    )
                    toggle_pwd_btn = gr.Button("👁️", scale=1, min_width=45)

                login_btn = gr.Button("Sign In", variant="primary")
                login_error_msg = gr.Markdown()
            gr.Column(scale=1)

    # =========================================================================
    # VIEW 2: MAIN CHAT & ANALYTICS APPLICATION
    # =========================================================================
    with gr.Column(visible=False) as app_view:
        with gr.Row(equal_height=True):
            user_banner = gr.Markdown()
            logout_btn = gr.Button(
                "🚪 Logout", 
                variant="stop", 
                elem_classes=["logout-btn"]
            )

        with gr.Tabs():
            # TAB 1: Chatbot Interface
            with gr.Tab("💬 Multi-Tenant Chatbot"):
                with gr.Row():
                    with gr.Column(scale=1, min_width=360):
                        trace_output = gr.Code(
                            label="Execution Trace",
                            language="json",
                            lines=30,
                            max_lines=30,
                        )

                    with gr.Column(scale=2):
                        chatbot = gr.Chatbot(
                            label="Agent Conversation",
                            height=430,
                            # type="messages",
                            allow_tags=False,
                        )
                        with gr.Row():
                            msg_input = gr.Textbox(
                                label="",
                                placeholder="Type a message and press Enter to send...",
                                container=False,
                                scale=3,
                                lines=1,
                                max_lines=3,
                                elem_classes=["scroll-input"],
                            )
                            submit_btn = gr.Button("Send", variant="primary", scale=1)

                msg_input.submit(
                    fn=chat_response,
                    inputs=[msg_input, chatbot, session_state],
                    outputs=[msg_input, chatbot, trace_output],
                )
                submit_btn.click(
                    fn=chat_response,
                    inputs=[msg_input, chatbot, session_state],
                    outputs=[msg_input, chatbot, trace_output],
                )

            # TAB 2: System Evaluation Benchmark
            with gr.Tab("📈 System Evaluation"):
                eval_btn = gr.Button("Run Benchmark", variant="secondary")
                metrics_summary = gr.Markdown()
                eval_details = gr.Code(label="Logs", language="json", lines=12)

                eval_btn.click(
                    fn=run_eval_benchmark,
                    inputs=[session_state],
                    outputs=[metrics_summary, eval_details],
                )

    # =========================================================================
    # EVENT BINDINGS
    # =========================================================================
    toggle_pwd_btn.click(
        fn=toggle_password_visibility,
        inputs=[pwd_is_secret],
        outputs=[password_box, toggle_pwd_btn, pwd_is_secret],
    )

    login_outputs = [
        login_view,
        app_view,
        session_state,
        login_error_msg,
        user_banner,
        username_box,
        password_box,
    ]

    login_btn.click(
        fn=login_handler,
        inputs=[username_box, password_box],
        outputs=login_outputs,
    )
    password_box.submit(
        fn=login_handler,
        inputs=[username_box, password_box],
        outputs=login_outputs,
    )

    logout_btn.click(
        fn=logout_handler,
        outputs=[
            login_view,
            app_view,
            session_state,
            login_error_msg,
            user_banner,
            username_box,
            password_box,
            chatbot,
            trace_output,
            metrics_summary,
            eval_details,
        ],
    )

demo.launch(
    inbrowser=True,
    css=CSS,
    theme=gr.themes.Soft(),
)