"""Display functions for TicketFairy CLI."""

import re

import clicycle


def display_dry_run_details(submission: dict, event_index: int) -> None:
    """Display the detailed information for a single dry-run submission."""
    clicycle.info(f"Event {event_index}: ID {submission['event_id']}")
    clicycle.info(f"URL: {submission['url']}")

    if "data" not in submission:
        return

    payload = submission["data"]
    clicycle.info("TicketFairy API Payload:")

    if "data" in payload and "attributes" in payload["data"]:
        attrs = payload["data"]["attributes"]
        image = attrs.get("image", "")

        # Display key fields
        key_fields = {
            "Title": attrs.get("title", "N/A"),
            "Venue": attrs.get("venue", "N/A"),
            "Ticket URL": attrs.get("url", "N/A"),
            "Address": attrs.get("address", "N/A"),
            "Start Date": attrs.get("startDate", "N/A"),
            "End Date": attrs.get("endDate", "N/A"),
            "Timezone": attrs.get("timezone", "N/A"),
            "Status": attrs.get("status", "N/A"),
            "Image URL": (f"{image[:60]}..." if len(image) > 60 else image) or "N/A",
            "Is Online": attrs.get("isOnline", "N/A"),
            "Hosted By": attrs.get("hostedBy", "N/A"),
        }
        clicycle.table([key_fields], title=f"Event {event_index} - TicketFairy Fields")

        if details := attrs.get("details"):
            clicycle.info("Description/Details:")
            details_clean = re.sub(r"<[^>]+>", "", details)
            clicycle.info(
                f"  {details_clean[:200]}..."
                if len(details_clean) > 200
                else f"  {details_clean}"
            )

    clicycle.info("Full JSON Payload (use this to debug API issues):")
    clicycle.json(payload, title="Complete TicketFairy API Payload")


def display_submission_results(
    submitter_name: str, result: dict, dry_run: bool
) -> None:
    """Display the results of a submission command."""
    clicycle.header(f"Submission Results for '{submitter_name}'")
    clicycle.info(f"Selector: {result['selector']}")
    clicycle.info(f"Total events processed: {result['total']}")

    if submitted := result.get("submitted"):
        clicycle.success(f"Successfully submitted: {len(submitted)}")
        if dry_run:
            clicycle.section("Dry Run - Would be submitted")
            for i, submission in enumerate(submitted, 1):
                display_dry_run_details(submission, i)
                if i < len(submitted):
                    print()  # separator between submissions
        else:
            # Display submitted events in a table format
            table_data = [
                {
                    "ID": s["event_id"],
                    "URL": s["url"],
                    "Status": s.get("status", "success"),
                }
                for s in submitted
            ]
            clicycle.table(table_data)

    if errors := result.get("errors"):
        clicycle.error(f"Errors: {len(errors)}")
        clicycle.section("Error Details")
        table_data = [
            {"Event ID": e["event_id"], "URL": e["url"], "Error": e["error"]}
            for e in errors
        ]
        clicycle.table(table_data)

    if not result.get("submitted") and not result.get("errors"):
        clicycle.warning("No events found to submit.")


def display_submission_status(
    total_events: int,
    unsubmitted_count: int,
    status_counts: list[tuple[str, int]]
) -> None:
    """Display submission status information."""
    clicycle.header("TicketFairy Submission Status")
    clicycle.info(f"Total cached events: {total_events}")
    clicycle.info(f"Unsubmitted events: {unsubmitted_count}")

    if status_counts:
        clicycle.section("Submission Status Breakdown")
        # Convert to table data
        table_data = []
        for status, count in status_counts:
            table_data.append({"Status": status.capitalize(), "Count": count})
        clicycle.table(table_data)
    else:
        clicycle.warning("No submissions found.")
