"use client";

import { useState } from "react";

/**
 * Circular speaker avatar. Shows the headshot if the image loads; falls back
 * to a branded initials circle if the image is missing or fails to load.
 * This keeps PerioVive cards looking intentional even before all photos exist.
 */

function initials(name: string): string {
  // Strip credentials after a comma ("Heidi Lobprise, DVM" -> "Heidi Lobprise")
  const clean = name.split(",")[0].trim();
  // Drop a leading "Dr." so we get real name initials, not "DL"
  const parts = clean.replace(/^Dr\.?\s+/i, "").split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0][0]?.toUpperCase() ?? "?";
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function SpeakerAvatar({
  src,
  name,
}: {
  src: string | null;
  name: string;
}) {
  const [failed, setFailed] = useState(false);
  const showImage = src && !failed;

  if (showImage) {
    return (
      <img
        src={src}
        alt={name}
        onError={() => setFailed(true)}
        className="h-14 w-14 rounded-full object-cover ring-2 ring-brand-200"
      />
    );
  }

  // Fallback: branded initials circle
  return (
    <div
      className="h-14 w-14 rounded-full ring-2 ring-brand-200 bg-brand-500 flex items-center justify-center text-white font-bold text-lg"
      aria-label={name}
    >
      {initials(name)}
    </div>
  );
}