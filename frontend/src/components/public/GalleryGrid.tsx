import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { publicGet } from "../../lib/api";

interface DisplayAlbum {
  id: number;
  title: string;
  desc: string;
  cover: string;
  images: { url: string; caption: string | null }[];
}

interface ApiAlbum {
  id: number;
  title: string;
  description: string | null;
  images: { id: number; image_url: string; caption: string | null }[];
}

const PLACEHOLDER_COVER =
  "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=500&fit=crop";

// Shown until live albums load; kept if the backend is unreachable.
const fallbackAlbums: DisplayAlbum[] = [
  {
    id: -1,
    title: "Annual Day 2025",
    desc: "A celebration of student drama, musical performances, and annual prize distributions.",
    cover: "https://images.unsplash.com/photo-1511578314322-379afb476865?w=500&fit=crop",
    images: [],
  },
  {
    id: -2,
    title: "Sports Meet 2025",
    desc: "Track events, obstacle races, and group sports competitions highlighting team spirit.",
    cover: "https://images.unsplash.com/photo-1502086223501-7ea6ecd79368?w=500&fit=crop",
    images: [],
  },
  {
    id: -3,
    title: "Classroom Activities",
    desc: "Interactive arts and crafts session, smart board lessons, and science projects.",
    cover: PLACEHOLDER_COVER,
    images: [],
  },
];

export default function GalleryGrid() {
  const [albums, setAlbums] = useState<DisplayAlbum[]>(fallbackAlbums);
  const [openAlbum, setOpenAlbum] = useState<DisplayAlbum | null>(null);

  useEffect(() => {
    publicGet<ApiAlbum[]>("/api/cms/albums").then((live) => {
      if (live && live.length > 0) {
        setAlbums(
          live.map((album) => ({
            id: album.id,
            title: album.title,
            desc: album.description ?? "",
            cover: album.images[0]?.image_url ?? PLACEHOLDER_COVER,
            images: album.images.map((img) => ({ url: img.image_url, caption: img.caption })),
          })),
        );
      }
    });
  }, []);

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {albums.map((album) => (
          <button
            key={album.id}
            type="button"
            onClick={() => album.images.length > 0 && setOpenAlbum(album)}
            className="bg-white rounded-3xl border border-slate-100 shadow-sm overflow-hidden hover:shadow-md transition group text-left"
          >
            <div className="relative overflow-hidden aspect-[4/3] bg-slate-100">
              <img
                src={album.cover}
                alt={album.title}
                loading="lazy"
                className="w-full h-full object-cover group-hover:scale-105 transition duration-500"
              />
              {album.images.length > 0 && (
                <div className="absolute inset-0 bg-gradient-to-t from-slate-900/50 to-transparent opacity-0 group-hover:opacity-100 transition duration-300 flex items-end p-6">
                  <span className="text-white font-bold text-sm bg-indigo-600 px-3 py-1.5 rounded-lg shadow">
                    View {album.images.length} Photo{album.images.length === 1 ? "" : "s"}
                  </span>
                </div>
              )}
            </div>
            <div className="p-6 space-y-2">
              <h3 className="text-xl font-extrabold text-slate-800">{album.title}</h3>
              <p className="text-sm text-slate-500 font-semibold leading-relaxed">{album.desc}</p>
            </div>
          </button>
        ))}
      </div>

      {openAlbum && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/80 flex items-center justify-center p-4"
          onClick={() => setOpenAlbum(null)}
        >
          <div
            className="bg-white rounded-3xl max-w-4xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-extrabold text-slate-800">{openAlbum.title}</h3>
              <button
                type="button"
                onClick={() => setOpenAlbum(null)}
                className="p-3 -m-1 rounded-xl hover:bg-slate-100 text-slate-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                aria-label="Close album"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {openAlbum.images.map((img, i) => (
                <figure key={i} className="space-y-1">
                  <img
                    src={img.url}
                    alt={img.caption ?? openAlbum.title}
                    loading="lazy"
                    className="w-full aspect-[4/3] object-cover rounded-2xl border border-slate-100"
                  />
                  {img.caption && (
                    <figcaption className="text-xs text-slate-500 font-semibold">{img.caption}</figcaption>
                  )}
                </figure>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
