type MarkerProps = {
  text: string;
};

export function Marker({ text }: MarkerProps) {
  return <p className="marker">{text}</p>;
}
