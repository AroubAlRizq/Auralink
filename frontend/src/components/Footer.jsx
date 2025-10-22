export default function Footer() {
  return (
    <footer className="w-full bg-[#4C2E91] text-white mt-12">
      <div className="max-w-6xl mx-auto py-8 px-6 flex flex-col md:flex-row justify-between items-center gap-4">
        {/* Left side */}
        <p className="text-sm text-white/80 text-center md:text-left">
          © {new Date().getFullYear()}{" "}
          <span className="font-semibold text-white">Auralink</span>.{" "}
          Powered by <span className="text-white font-medium">Our Team</span>.
        </p>

        {/* Right side */}
        <div className="flex gap-5 text-sm text-white/80 text-center md:text-right">
          <a
            href="#"
            className="hover:text-white transition-colors duration-200"
          >
            Privacy Policy
          </a>
          <a
            href="#"
            className="hover:text-white transition-colors duration-200"
          >
            Terms
          </a>
          <a
            href="#"
            className="hover:text-white transition-colors duration-200"
          >
            Contact
          </a>
        </div>
      </div>
    </footer>
  );
}