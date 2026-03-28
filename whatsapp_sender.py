"""
WhatsApp message sender using Twilio.
"""

from twilio.rest import Client


class WhatsAppSender:
    """Sends WhatsApp messages via Twilio."""

    # Twilio body limit is 1600 chars, we use 1500 for safety margin
    MAX_BODY_LENGTH = 1500

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_number: str,
    ):
        self.from_number = from_number
        self.to_number = to_number
        self.client = None

        if account_sid and auth_token:
            try:
                self.client = Client(account_sid, auth_token)
            except Exception as e:
                print(f"Error initializing Twilio client: {e}")

    def send(self, text: str) -> bool:
        """
        Send a single WhatsApp message.
        Truncates if over MAX_BODY_LENGTH.
        Returns True if successful.
        """
        if not self.client:
            print("Twilio client not initialized")
            return False

        if not self.from_number or not self.to_number:
            print("WhatsApp numbers not configured")
            return False

        # Truncate if needed
        if len(text) > self.MAX_BODY_LENGTH:
            text = text[: self.MAX_BODY_LENGTH - 3] + "..."

        try:
            message = self.client.messages.create(
                body=text,
                from_=self.from_number,
                to=self.to_number,
            )
            print(f"WhatsApp sent (SID: {message.sid})")
            return True
        except Exception as e:
            print(f"Error sending WhatsApp: {e}")
            return False

    def send_chunks(self, text: str, max_chars: int = 1500) -> bool:
        """
        Send a long message in multiple chunks if needed.
        Splits gracefully at newlines when possible.
        Returns True if all chunks sent successfully.
        """
        if not self.client:
            print("Twilio client not initialized")
            return False

        if len(text) <= max_chars:
            return self.send(text)

        # Split into chunks
        chunks = self._split_text(text, max_chars)
        all_success = True

        for i, chunk in enumerate(chunks):
            if i > 0:
                # Add part indicator for subsequent chunks
                chunk = f"(continued {i + 1}/{len(chunks)})\n\n{chunk}"

            success = self.send(chunk)
            if not success:
                all_success = False

        return all_success

    def _split_text(self, text: str, max_chars: int) -> list[str]:
        """Split text into chunks, preferring to break at newlines."""
        chunks = []
        remaining = text

        while remaining:
            if len(remaining) <= max_chars:
                chunks.append(remaining)
                break

            # Find a good break point
            chunk = remaining[:max_chars]

            # Try to break at a newline
            last_newline = chunk.rfind("\n")
            if last_newline > max_chars // 2:
                # Break at newline if it's not too early
                chunk = remaining[:last_newline]
                remaining = remaining[last_newline + 1:]
            else:
                # Break at space
                last_space = chunk.rfind(" ")
                if last_space > max_chars // 2:
                    chunk = remaining[:last_space]
                    remaining = remaining[last_space + 1:]
                else:
                    # Hard break
                    remaining = remaining[max_chars:]

            chunks.append(chunk.strip())

        return chunks
