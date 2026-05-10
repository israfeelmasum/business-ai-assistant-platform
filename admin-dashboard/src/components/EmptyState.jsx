export default function EmptyState({ icon = '📭', title, description, action }) {
  return (
    <div className="text-center py-16">
      <span className="text-5xl block mb-4">{icon}</span>
      <h3 className="text-lg font-semibold text-gray-700">{title}</h3>
      {description && <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
