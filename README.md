# Project: Azure Retirement Announcement

This project monitors an RSS feed for retirement announcements related to Azure services. It retrieves updates from the feed and performs two actions:

1. **Email Notifications**: Sends email notifications to specified recipients with details of the retirement announcements.
2. **Jira Ticket Creation**: Creates Jira tickets for each retirement announcement, capturing essential details in the ticket.

![alt text](RssAzFuncArch.svg)

## Running Locally

To run the project locally, follow these steps:

1. Create a Python virtual environment:

    ```bash
    python -m venv venv
    ```

2. Activate the virtual environment:

    - On Windows:

    ```bash
    .venv\Scripts\activate
    ```

    - On macOS/Linux:

    ```bash
    source .venv/bin/activate
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Start the Azure Functions app:

    ```bash
    func start
    ```

## Deploying Azure Function

To deploy the Azure Function, follow these steps:

1. Set environment variables using Azure CLI:

    ```bash
    az functionapp config appsettings set --name func-internal12 -g 3as-internal --settings @settings.json
    ```

2. Deploy the function:

    ```bash
    func azure functionapp publish <FunctionAppName>
    ```
    
## Notification Methods

This project supports two notification methods:

### Email Notifications

Email notifications are sent using the Azure Communication Services. Recipients receive an email with details of the retirement announcements.

### Jira Ticket Creation

Jira tickets are created automatically for each retirement announcement. The project uses the Jira REST API to create tickets, capturing relevant information such as summary, description, priority, and due date.
