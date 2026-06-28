type AttachmentProps = {
  title: string;
  subtitle?: string;
};

export function Attachment({ title, subtitle }: AttachmentProps) {
  return (
    <div className="attachment">
      <p className="attachment-title">{title}</p>
      {subtitle ? <p className="attachment-subtitle">{subtitle}</p> : null}
    </div>
  );
}
