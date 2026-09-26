import { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: 'https://www.xaiote.com', lastModified: new Date(), changeFrequency: 'weekly', priority: 1 },
    { url: 'https://www.xaiote.com/product', lastModified: new Date(), changeFrequency: 'weekly', priority: 0.8 },
    { url: 'https://www.xaiote.com/how-it-works', lastModified: new Date(), changeFrequency: 'weekly', priority: 0.8 },
    { url: 'https://www.xaiote.com/solutions', lastModified: new Date(), changeFrequency: 'weekly', priority: 0.8 },
    { url: 'https://www.xaiote.com/industries', lastModified: new Date(), changeFrequency: 'weekly', priority: 0.8 },
    { url: 'https://www.xaiote.com/security', lastModified: new Date(), changeFrequency: 'weekly', priority: 0.8 },
    { url: 'https://www.xaiote.com/resources', lastModified: new Date(), changeFrequency: 'weekly', priority: 0.8 },
    { url: 'https://www.xaiote.com/company', lastModified: new Date(), changeFrequency: 'monthly', priority: 0.5 },
    { url: 'https://www.xaiote.com/contact', lastModified: new Date(), changeFrequency: 'yearly', priority: 0.5 }
  ];
}
