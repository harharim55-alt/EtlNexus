interface EmptyStateProps {
  message?: string;
}

export function EmptyState({
  message = "Select a pipeline to view details",
}: EmptyStateProps) {
  return (
    <div className="flex h-full items-center justify-center text-slate-500">
      <p className="text-sm">{message}</p>
    </div>
  );
}
