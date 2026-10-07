import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type ChangeEvent } from "react";

import { listingsApi } from "../api/listings";
import { resolveImageUrl } from "../api/client";
import { listingKeys } from "../hooks/useListings";
import { useToast } from "../hooks/useToast";
import { errorMessage } from "../lib/errors";
import { ALLOWED_IMAGE_TYPES, MAX_IMAGES, validateImageFile } from "../lib/images";
import type { ListingImage } from "../types/api";
import { Spinner } from "./States";

export function PhotosManager({ listingId, images }: { listingId: number; images: ListingImage[] }) {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [problems, setProblems] = useState<string[]>([]);
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: listingKeys.detail(listingId) });
    void queryClient.invalidateQueries({ queryKey: listingKeys.all });
  };

  const upload = useMutation({
    // One at a time keeps the order predictable and stays well under the server's limits.
    mutationFn: async (files: File[]) => {
      const failures: string[] = [];
      for (const file of files) {
        try {
          await listingsApi.uploadImage(listingId, file);
        } catch (error) {
          failures.push(`${file.name}: ${errorMessage(error)}`);
        }
      }
      return failures;
    },
    onSuccess: (failures, files) => {
      const uploaded = files.length - failures.length;
      if (uploaded > 0) notify({ title: `${uploaded} photo${uploaded === 1 ? "" : "s"} uploaded`, tone: "success" });
      setProblems((current) => [...current, ...failures]);
    },
    onSettled: refresh,
  });

  const remove = useMutation({
    mutationFn: (imageId: number) => listingsApi.deleteImage(listingId, imageId),
    onError: (error) => notify({ title: "Couldn't delete photo", description: errorMessage(error), tone: "error" }),
    onSettled: refresh,
  });

  const onFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    event.target.value = ""; // allow picking the same file again
    const invalid = files.map(validateImageFile).filter((p): p is string => p !== null);
    const valid = files.filter((f) => validateImageFile(f) === null).slice(0, Math.max(0, MAX_IMAGES - images.length));
    setProblems(invalid);
    if (valid.length) upload.mutate(valid);
  };

  return (
    <section aria-labelledby="photos-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="photos-heading" className="text-lg font-semibold">Photos</h2>
          <p className="text-sm text-slate-500">JPEG, PNG or WebP, up to 5 MB each, {MAX_IMAGES} max. The first photo is the cover.</p>
        </div>
        <button
          type="button"
          className="btn-secondary"
          disabled={upload.isPending || images.length >= MAX_IMAGES}
          onClick={() => inputRef.current?.click()}
        >
          {upload.isPending ? <Spinner className="h-4 w-4" /> : "+"} Add photos
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_IMAGE_TYPES.join(",")}
          multiple
          className="sr-only"
          aria-label="Upload photos"
          onChange={onFiles}
        />
      </div>

      {problems.length > 0 && (
        <ul role="alert" className="space-y-1 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {problems.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      )}

      {images.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
          No photos yet. Listings with photos get far more visit requests.
        </p>
      ) : (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {images.map((image, i) => (
            <li key={image.id} className="group relative overflow-hidden rounded-lg border border-slate-200">
              <img src={resolveImageUrl(image.url)} alt={`Photo ${i + 1}`} className="aspect-[4/3] w-full object-cover" />
              {i === 0 && <span className="absolute top-2 left-2 rounded bg-black/60 px-1.5 py-0.5 text-xs text-white">Cover</span>}
              <button
                type="button"
                aria-label={`Delete photo ${i + 1}`}
                disabled={remove.isPending}
                onClick={() => remove.mutate(image.id)}
                className="absolute top-2 right-2 grid h-7 w-7 place-items-center rounded-full bg-white/90 text-slate-700 shadow hover:bg-red-50 hover:text-red-700"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
