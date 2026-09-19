import "./globals.css";

export const metadata = {
  title: "CareerOps",
  description: "Career intelligence dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
