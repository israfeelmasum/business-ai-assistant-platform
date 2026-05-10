import { useAuth } from '../context/AuthContext';

export default function Header({ title, subtitle }) {
  const { client } = useAuth();
  return (
    <header className="bg-white border-b border-gray-200 px-8 py-5 flex justify-between items-center">
      <div>
        <h1 className="text-xl font-bold text-gray-900">{title}</h1>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-bold">
          {(client?.name || 'A')[0].toUpperCase()}
        </div>
      </div>
    </header>
  );
}
