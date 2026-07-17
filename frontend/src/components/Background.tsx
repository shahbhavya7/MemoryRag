// The ambient animated backdrop — a dark base with a few slowly drifting,
// heavily-blurred color blobs. This is what the glass panels blur; a flat
// background would defeat the whole effect. The drift is the single allowed
// infinite animation, and it's frozen under prefers-reduced-motion (see CSS).

export default function Background() {
  return (
    <div className="bg-aurora" aria-hidden="true">
      <div className="bg-blob b1" />
      <div className="bg-blob b2" />
      <div className="bg-blob b3" />
    </div>
  );
}
