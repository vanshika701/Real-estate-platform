import { useState } from "react";

import { resolveImageUrl } from "../api/client";
import type { ListingImage } from "../types/api";

export function ImageGallery({ images, title }: { images: ListingImage[]; title: string }) {
  const [index, setIndex] = useState(0);

  if (images.length === 0) {
    return (
      <div className="grid aspect-[16/9] place-items-center rounded-xl bg-slate-100 text-slate-400">
        No photos yet
      </div>
    );
  }

  const current = images[Math.min(index, images.length - 1)];
  const go = (delta: number) => setIndex((i) => (i + delta + images.length) % images.length);

  return (
    <section aria-label="Photos" className="space-y-3">
      <div className="relative overflow-hidden rounded-xl bg-slate-100">
        <img
          src={current ? resolveImageUrl(current.url) : undefined}
          alt={`${title}, photo ${index + 1} of ${images.length}`}
          className="aspect-[16/9] w-full object-cover"
        />
        {images.length > 1 && (
          <>
            <button
              type="button"
              aria-label="Previous photo"
              onClick={() => go(-1)}
              className="absolute top-1/2 left-3 grid h-10 w-10 -translate-y-1/2 place-items-center rounded-full bg-white/90 text-slate-800 shadow hover:bg-white"
            >
              ‹
            </button>
            <button
              type="button"
              aria-label="Next photo"
              onClick={() => go(1)}
              className="absolute top-1/2 right-3 grid h-10 w-10 -translate-y-1/2 place-items-center rounded-full bg-white/90 text-slate-800 shadow hover:bg-white"
            >
              ›
            </button>
            <span className="absolute right-3 bottom-3 rounded-full bg-black/60 px-2.5 py-1 text-xs font-medium text-white">
              {index + 1} / {images.length}
            </span>
          </>
        )}
      </div>

      {images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {images.map((image, i) => (
            <button
              key={image.id}
              type="button"
              aria-label={`Show photo ${i + 1}`}
              aria-current={i === index}
              onClick={() => setIndex(i)}
              className={`shrink-0 overflow-hidden rounded-lg border-2 transition ${
                i === index ? "border-brand-600" : "border-transparent opacity-70 hover:opacity-100"
              }`}
            >
              <img src={resolveImageUrl(image.url)} alt="" className="h-16 w-24 object-cover" loading="lazy" />
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
