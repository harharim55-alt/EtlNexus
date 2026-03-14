import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function isApiPipeline(category: string | null | undefined): boolean {
  return category?.toLowerCase().includes("api") ?? false;
}
