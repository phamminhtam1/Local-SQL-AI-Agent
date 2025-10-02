from mcp import types
from mcp.server.fastmcp import FastMCP
import requests
from api.finance_api import get_stock_info, get_unemployment, get_cpi, get_nonfarm_payroll, get_fed_rate

API_BASE = "http://localhost:8000"  

# Create an MCP server
mcp = FastMCP(name="MCP_server", host="127.0.0.1", port=5050)


@mcp.tool()
def messaging_create_user(email: str, name: str):
    """
    Create a new user in the system.

    Args:
        email (str): Email address of the user. Must be unique.
        name (str): Full name of the user.

    Returns:
        dict: JSON response containing the created user's information.
    """
    resp = requests.post(f"{API_BASE}/users/", json={"email": email, "name": name})
    return resp.json()


@mcp.tool()
def messaging_get_user_by_email(email: str):
    """
    Retrieve details of a user by their email address.

    Args:
        email (str): Email address of the user.

    Returns:
        dict: JSON response containing the user's information if found.
    """
    resp = requests.get(f"{API_BASE}/users/{email}")
    return resp.json()


@mcp.tool()
def messaging_get_all_users():
    """
    Retrieve a list of all users in the system.

    Returns:
        dict: JSON response containing all users' information.
    """
    resp = requests.get(f"{API_BASE}/users/")
    return resp.json()


@mcp.tool()
def messaging_send_message(sender_id: str, recipients: list[str], subject: str, content: str):
    """
    Send a message from one user to one or more recipients.

    Args:
        sender_id (str): ID of the sender.
        recipients (list[str]): List of recipient IDs.
        subject (str): Subject/title of the message.
        content (str): Content/body of the message.

    Returns:
        dict: JSON response containing the created message details.
    """
    resp = requests.post(f"{API_BASE}/messages/", json={
        "sender_id": sender_id,
        "recipients": recipients,
        "subject": subject,
        "content": content
    })
    return resp.json()


@mcp.tool()
def messaging_get_all_sent_message(sender_id: str):
    """
    Retrieve all messages sent by a specific user.

    Args:
        sender_id (str): ID of the sender.

    Returns:
        dict: JSON response containing all sent messages.
    """
    resp = requests.get(f"{API_BASE}/messages/sent/{sender_id}")
    return resp.json()


@mcp.tool()
def messaging_view_inbox(user_id: str):
    """
    Retrieve all inbox messages of a specific user.

    Args:
        user_id (str): ID of the user.

    Returns:
        dict: JSON response containing inbox messages.
    """
    resp = requests.get(f"{API_BASE}/messages/inbox/{user_id}")
    return resp.json()


@mcp.tool()
def messaging_get_unread_message(recipient_id: str):
    """
    Retrieve all unread messages for a specific recipient.

    Args:
        recipient_id (str): ID of the recipient.

    Returns:
        dict: JSON response containing unread messages.
    """
    resp = requests.get(f"{API_BASE}/messages/unread/{recipient_id}")
    return resp.json()


@mcp.tool()
def messaging_get_message_with_recipients(message_id: str):
    """
    Retrieve a specific message along with all its recipients.

    Args:
        message_id (str): ID of the message.

    Returns:
        dict: JSON response containing the message details and recipients.
    """
    resp = requests.get(f"{API_BASE}/messages/{message_id}/recipients")
    return resp.json()


@mcp.tool()
def messaging_mark_as_read(message_id: str, recipient_id: str):
    """
    Mark a specific message as read for a given recipient.

    Args:
        message_id (str): ID of the message.
        recipient_id (str): ID of the recipient who read the message.

    Returns:
        dict: JSON response confirming the read status.
    """
    resp = requests.post(f"{API_BASE}/messages/{message_id}/read", json={"recipient_id": recipient_id})
    return resp.json()


@mcp.tool()
def finance_get_stock_info_tool(symbol: str):
    """
    Retrieve stock information for a given symbol.

    Args:
        symbol (str): Stock ticker symbol (e.g., "AAPL", "GOO).

    Returns:
        dict: JSON response containing stock price and related details.
    """
    return get_stock_info(symbol)


@mcp.tool()
def finance_get_cpi_tool(month: int, year: int):
    """
    Retrieve Consumer Price Index (CPI) data for a specific month and year.

    Args:
        month (int): Month (1-12).
        year (int): Year (e.g., 2025).

    Returns:
        dict: JSON response containing CPI information.
    """
    return get_cpi(month, year)


@mcp.tool()
def finance_get_fed_rate_tool(month: int, year: int):
    """
    Retrieve the Federal Reserve interest rate for a given month and year.

    Args:
        month (int): Month (1-12).
        year (int): Year (e.g., 2025).

    Returns:
        dict: JSON response containing the Fed interest rate.
    """
    return get_fed_rate(month, year)


@mcp.tool()
def finance_get_nonfarm_payroll_tool(month: int, year: int):
    """
    Retrieve Nonfarm Payroll employment data for a specific month and year.

    Args:
        month (int): Month (1-12).
        year (int): Year (e.g., 2025).

    Returns:
        dict: JSON response containing Nonfarm Payroll data.
    """
    return get_nonfarm_payroll(month, year)


@mcp.tool()
def finance_get_unemployment_tool(month: int, year: int):
    """
    Retrieve unemployment rate for a specific month and year.

    Args:
        month (int): Month (1-12).
        year (int): Year (e.g., 2025).

    Returns:
        dict: JSON response containing unemployment rate.
    """
    return get_unemployment(month, year)


# Run the MCP server
if __name__ == "__main__":
    mcp.run(transport="sse")
