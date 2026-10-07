export const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 5 * 1024 * 1024;
export const MAX_IMAGES = 10;

/** Client-side checks give instant feedback; the server re-checks (including the file's real type). */
export function validateImageFile(file: File): string | null {
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) return `${file.name}: only JPEG, PNG or WebP`;
  if (file.size > MAX_BYTES) return `${file.name}: larger than 5 MB`;
  return null;
}
