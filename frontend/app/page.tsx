import Nav from "./components/Nav";
import Hero from "./components/Hero";
import Features from "./components/Features";
import Playground from "./components/Playground";
import Benchmarks from "./components/Benchmarks";
import CodeShowcase from "./components/CodeShowcase";
import Compat from "./components/Compat";
import Footer from "./components/Footer";

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <div className="rope-divider mx-auto max-w-4xl" />
        <Features />
        <Playground />
        <Benchmarks />
        <CodeShowcase />
        <Compat />
      </main>
      <Footer />
    </>
  );
}
