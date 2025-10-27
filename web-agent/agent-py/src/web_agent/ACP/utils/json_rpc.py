"""JSON-RPC utilities for ACP communication.

This module provides utilities for handling JSON-RPC 2.0 protocol
messages, including request/response formatting, error handling,
and validation.
"""

import json
import logging
from typing import Any, Dict, Optional, Union

from ..protocol.types import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    JSONRPCError,
    ACPErrorCode,
)

logger = logging.getLogger(__name__)


class JSONRPCProcessor:
    """JSON-RPC message processor."""

    def __init__(self):
        """Initialize the JSON-RPC processor."""
        self.request_handlers = {}
        self.notification_handlers = {}

    def register_request_handler(self, method: str, handler):
        """Register a request handler.

        Args:
            method: Method name
            handler: Async handler function
        """
        self.request_handlers[method] = handler

    def register_notification_handler(self, method: str, handler):
        """Register a notification handler.

        Args:
            method: Method name
            handler: Async handler function
        """
        self.notification_handlers[method] = handler

    def parse_message(self, data: str) -> Union[JSONRPCRequest, JSONRPCNotification]:
        """Parse a JSON-RPC message.

        Args:
            data: Raw JSON string

        Returns:
            Parsed JSON-RPC message

        Raises:
            ValueError: If message is invalid JSON-RPC
        """
        try:
            message_data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

        # Validate JSON-RPC 2.0 format
        if not isinstance(message_data, dict):
            raise ValueError("Message must be a JSON object")

        if message_data.get("jsonrpc") != "2.0":
            raise ValueError("Missing or invalid jsonrpc version")

        method = message_data.get("method")
        if not method:
            raise ValueError("Missing method")

        params = message_data.get("params")
        if params is not None and not isinstance(params, dict):
            raise ValueError("Params must be an object or null")

        # Determine if it's a request or notification
        if "id" in message_data:
            return JSONRPCRequest(**message_data)
        else:
            return JSONRPCNotification(**message_data)

    def create_response(
        self, result: Any, request_id: Optional[Union[str, int]] = None
    ) -> JSONRPCResponse:
        """Create a JSON-RPC response.

        Args:
            result: Response result
            request_id: Request ID

        Returns:
            JSON-RPC response
        """
        return JSONRPCResponse(result=result, id=request_id)

    def create_error(
        self,
        code: ACPErrorCode,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        request_id: Optional[Union[str, int]] = None,
    ) -> JSONRPCResponse:
        """Create a JSON-RPC error response.

        Args:
            code: Error code
            message: Error message
            data: Optional error data
            request_id: Request ID

        Returns:
            JSON-RPC error response
        """
        error = JSONRPCError(code=code, message=message, data=data)
        return JSONRPCResponse(error=error, id=request_id)

    def create_notification(
        self, method: str, params: Optional[Dict] = None
    ) -> JSONRPCNotification:
        """Create a JSON-RPC notification.

        Args:
            method: Method name
            params: Method parameters

        Returns:
            JSON-RPC notification
        """
        return JSONRPCNotification(method=method, params=params)

    def validate_request(self, request: JSONRPCRequest) -> Optional[JSONRPCResponse]:
        """Validate a JSON-RPC request.

        Args:
            request: JSON-RPC request to validate

        Returns:
            Error response if invalid, None if valid
        """
        # Check if method is registered
        if request.method not in self.request_handlers:
            return self.create_error(
                code=ACPErrorCode.METHOD_NOT_FOUND,
                message=f"Method '{request.method}' not found",
                request_id=request.id,
            )

        return None

    def validate_notification(self, notification: JSONRPCNotification) -> bool:
        """Validate a JSON-RPC notification.

        Args:
            notification: JSON-RPC notification to validate

        Returns:
            True if valid, False otherwise
        """
        # Check if method is registered
        return notification.method in self.notification_handlers

    async def process_message(self, data: str) -> Optional[str]:
        """Process a JSON-RPC message.

        Args:
            data: Raw JSON string

        Returns:
            JSON-RPC response string or None for notifications
        """
        try:
            # Parse message
            message = self.parse_message(data)

            # Handle request
            if isinstance(message, JSONRPCRequest):
                # Validate request
                error_response = self.validate_request(message)
                if error_response:
                    return error_response.model_dump_json()

                # Get handler
                handler = self.request_handlers[message.method]

                # Execute handler
                try:
                    result = await handler(message.params or {})
                    response = self.create_response(result, message.id)
                    return response.model_dump_json()

                except Exception as e:
                    logger.error(f"Handler error for {message.method}: {e}")
                    error_response = self.create_error(
                        code=ACPErrorCode.INTERNAL_ERROR,
                        message=f"Handler error: {str(e)}",
                        request_id=message.id,
                    )
                    return error_response.model_dump_json()

            # Handle notification
            elif isinstance(message, JSONRPCNotification):
                # Validate notification
                if not self.validate_notification(message):
                    logger.warning(f"Unknown notification method: {message.method}")
                    return None

                # Get handler
                handler = self.notification_handlers[message.method]

                # Execute handler (no response expected)
                try:
                    await handler(message.params or {})
                except Exception as e:
                    logger.error(
                        f"Notification handler error for {message.method}: {e}"
                    )

                return None

        except ValueError as e:
            # Parse error
            error_response = self.create_error(
                code=ACPErrorCode.INVALID_REQUEST,
                message=str(e),
            )
            return error_response.model_dump_json()

        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error processing message: {e}")
            error_response = self.create_error(
                code=ACPErrorCode.INTERNAL_ERROR,
                message=f"Internal error: {str(e)}",
            )
            return error_response.model_dump_json()


def create_json_rpc_error(
    code: ACPErrorCode,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    request_id: Optional[Union[str, int]] = None,
) -> str:
    """Create a JSON-RPC error response string.

    Args:
        code: Error code
        message: Error message
        data: Optional error data
        request_id: Request ID

    Returns:
        JSON-RPC error response string
    """
    error = JSONRPCError(code=code, message=message, data=data)
    response = JSONRPCResponse(error=error, id=request_id)
    return response.model_dump_json()


def create_json_rpc_response(
    result: Any, request_id: Optional[Union[str, int]] = None
) -> str:
    """Create a JSON-RPC response string.

    Args:
        result: Response result
        request_id: Request ID

    Returns:
        JSON-RPC response string
    """
    response = JSONRPCResponse(result=result, id=request_id)
    return response.model_dump_json()


def create_json_rpc_notification(method: str, params: Optional[Dict] = None) -> str:
    """Create a JSON-RPC notification string.

    Args:
        method: Method name
        params: Method parameters

    Returns:
        JSON-RPC notification string
    """
    notification = JSONRPCNotification(method=method, params=params)
    return notification.model_dump_json()


def is_json_rpc_request(data: str) -> bool:
    """Check if data is a valid JSON-RPC request.

    Args:
        data: JSON string to check

    Returns:
        True if valid JSON-RPC request, False otherwise
    """
    try:
        message_data = json.loads(data)
        return (
            isinstance(message_data, dict)
            and message_data.get("jsonrpc") == "2.0"
            and "method" in message_data
            and "id" in message_data
        )
    except (json.JSONDecodeError, TypeError):
        return False


def is_json_rpc_notification(data: str) -> bool:
    """Check if data is a valid JSON-RPC notification.

    Args:
        data: JSON string to check

    Returns:
        True if valid JSON-RPC notification, False otherwise
    """
    try:
        message_data = json.loads(data)
        return (
            isinstance(message_data, dict)
            and message_data.get("jsonrpc") == "2.0"
            and "method" in message_data
            and "id" not in message_data
        )
    except (json.JSONDecodeError, TypeError):
        return False
