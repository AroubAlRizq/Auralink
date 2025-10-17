export default function Footer() {
  return (
    <footer className="w-full border-t border-gray-100 bg-white text-gray-600 mt-10">
      <div className="max-w-6xl mx-auto py-8 px-6 flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="text-sm">
          © {new Date().getFullYear()} <span className="font-semibold text-sdaiapurple">Auralink</span>.  
          Powered by <span className="text-sdaiateal font-medium">Our Team</span>.
        </p>

        <div className="flex gap-5 text-sm">
          <a href="#" className="hover:text-sdaiapurple transition">Privacy Policy</a>
          <a href="#" className="hover:text-sdaiapurple transition">Terms</a>
          <a href="#" className="hover:text-sdaiapurple transition">Contact</a>
        </div>
      </div>
    </footer>
  );
}
