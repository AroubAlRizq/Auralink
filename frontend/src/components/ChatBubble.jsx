export default function ChatBubble() {
  return (
    <button
      title="Open Chat"
      className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-sdaiapurple text-white shadow-lg
                 hover:bg-sdaiablue flex items-center justify-center transition"
      onClick={() => window.location.assign("/chat")}
    >
      💬
    </button>
  );
}
