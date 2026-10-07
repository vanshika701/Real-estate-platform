import { ApiError } from "../api/client";

/** A message that's safe and useful to show a user, for any thrown value. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "Can't reach the server. Check your connection.";
  return "Something went wrong.";
}
