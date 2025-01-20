from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vuetify

# -----------------------------------------------------------------------------
# Get a server to work with
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")

# -----------------------------------------------------------------------------
# Close the server
# -----------------------------------------------------------------------------

def close_server():
    server.stop()

# -----------------------------------------------------------------------------
# Change auth_key
# -----------------------------------------------------------------------------

async def change_auth_key():
    print("Changing auth key to 'Goodbye'")  
    await server.set_new_auth_key("Goodbye")

# -----------------------------------------------------------------------------
# Get the current auth_key
# -----------------------------------------------------------------------------

async def get_auth_key():
    print("Retrieving auth key")

    # Hardcode the verification information (username, password and client IP)
    # But ideally, this information should be retrieved from the client
    
    username = "admin"
    password = "admin"
    client_ip = "127.0.0.1"

    await server.get_auth_key(username, password, client_ip)

# -----------------------------------------------------------------------------
# Check username
# -----------------------------------------------------------------------------

async def check_username():
    print("Checking username")

    # Hardcode the verification information (username)
    # But ideally, this information should be retrieved from the client
    
    username = "admin"

    await server.check_username(username)

# -----------------------------------------------------------------------------
# Start server async function
# -----------------------------------------------------------------------------

async def start_server_async(port: int, auth_key: str):
    print(f"Starting OoD Analyzer server (async) at http://localhost:{port}/index.html")
    return await server.start(exec_mode="task", port=port, auth_key=auth_key)

# -----------------------------------------------------------------------------
# Main async function
# -----------------------------------------------------------------------------

async def main_async(port: int, auth_key: str):
    
    # Start the server
    await start_server_async(port, auth_key=auth_key)

# -----------------------------------------------------------------------------
# UI Layout (Vuetify 2)
# -----------------------------------------------------------------------------

with SinglePageLayout(server) as layout:
    layout.title.set_text("Authentication Management Panel (Example)")
    
    with layout.toolbar:
        vuetify.VSpacer()
        vuetify.VBtn(
            "Exit Application",
            click=close_server,
            color="red darken-1",
            dark=True,
            elevation=2,
            rounded=True,
            prepend_icon="mdi-exit-to-app",
            classes="ma-2"
        )
    
    with layout.content:
        with vuetify.VContainer(
            fluid=True,
            classes="fill-height",
            style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f2 100%);"
        ):
            with vuetify.VRow(
                classes="fill-height justify-center align-center",
                style="min-height: 100vh;"
            ):
                with vuetify.VCol(
                    cols="12",
                    sm="8",
                    md="6",
                    lg="4"
                ):
                    with vuetify.VCard(
                        elevation=10,
                        rounded="lg",
                        classes="pa-6",
                        style="""
                            border-radius: 16px;
                            backdrop-filter: blur(10px);
                            background: rgba(255, 255, 255, 0.95);
                        """
                    ):
                        vuetify.VCardTitle(
                            "Control Panel",
                            classes="text-h4 font-weight-bold text-center primary--text mb-2 align-self-center justify-center width-100"
                        )
                        vuetify.VCardSubtitle(
                            "Manage authentication tasks with the options below",
                            classes="text-subtitle-1 text-center mb-6 grey--text text--darken-1"
                        )
                        vuetify.VDivider(classes="mb-6")
                        
                        with vuetify.VRow(classes="justify-center"):
                            with vuetify.VCol(cols="12"):
                                vuetify.VBtn(
                                    "Change Key",
                                    click=change_auth_key,
                                    color="primary",
                                    x_large=True,
                                    block=True,
                                    elevation=2,
                                    rounded=True,
                                    prepend_icon="mdi-key-change",
                                    classes="mb-4 py-6",
                                    style="font-size: 1.1rem;"
                                )
                                
                                vuetify.VBtn(
                                    "Get Key",
                                    click=get_auth_key,
                                    color="success darken-1",
                                    x_large=True,
                                    block=True,
                                    elevation=2,
                                    rounded=True,
                                    prepend_icon="mdi-key",
                                    classes="mb-4 py-6",
                                    style="font-size: 1.1rem;"
                                )
                                
                                vuetify.VBtn(
                                    "Check Username",
                                    click=check_username,
                                    color="warning darken-1",
                                    x_large=True,
                                    block=True,
                                    elevation=2,
                                    rounded=True,
                                    prepend_icon="mdi-account-check",
                                    classes="mb-4 py-6",
                                    style="font-size: 1.1rem;"
                                )
                        
                        # Footer section
                        vuetify.VDivider(classes="mt-6 mb-4")
                        vuetify.VCardText(
                            "Secure Authentication Management System",
                            classes="text-caption text-center grey--text"
                        )

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Loopback address/localhost 8080 (local machine only).
    # server.start(auth_key="key", port=ENTER_YOUR_PORT_INTEGER, username="admin", password="admin", client_ip="127.0.0.1", allowed_ips=["123","456"])
    # server.start(auth_key="key", username="admin", password="admin", client_ip="127.0.0.1", allowed_ips=["123","456"])

    # All available network interfaces (publicly accessible)
    # server.start(host='0.0.0.0', port=ENTER_YOUR_PORT_INTEGER, auth_key="key", username="admin", password="admin", client_ip="127.0.0.1", allowed_ips=["123","456"])
    server.start(host='0.0.0.0', auth_key="key", username="admin", password="admin", client_ip="127.0.0.1", allowed_ips=["123","456"])

    # http://129.114.109.159:8080/index.html