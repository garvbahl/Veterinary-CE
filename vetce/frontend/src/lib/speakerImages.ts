/**
 * Maps PerioVive presenter names to their headshot images.
 *
 * Keys must EXACTLY match the `presenter` string on the listing (from the DB),
 * including credentials. Values are paths under /public.
 *
 * To add a photo: download the headshot into frontend/public/speakers/,
 * then set the filename below. Missing/empty entries degrade gracefully —
 * the card still "pops" (badge + tint + border) but shows no headshot.
 */
export const SPEAKER_IMAGES: Record<string, string> = {
  "Dr. Grace Brown": "/speakers/grace-brown.jpg",
  "Dr. Jan Bellows": "/speakers/jan-bellows.jpg",
  "Erin Vicari, VMD, DAVDC": "/speakers/erin-vicari.jpg",
  "Dr. Vanessa Aberman": "/speakers/vanessa-aberman.jpg",
  "Sheena Davis, LVT, VTS (Dentistry) CFVP": "/speakers/sheena-davis.jpg",
  "Heidi Lobprise, DVM, DAVDC": "/speakers/heidi-lobprise.jpg",
  "Mary Berg, RVT, VTS (Dentistry)": "/speakers/mary-berg.jpg",
  "Dr. Brett Beckman": "/speakers/brett-beckman.jpg",
};

/** Look up a speaker image by presenter name, trimming whitespace. */
export function speakerImage(presenter: string | null): string | null {
  if (!presenter) return null;
  return SPEAKER_IMAGES[presenter.trim()] ?? null;
}