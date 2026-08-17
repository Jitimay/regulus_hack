import { z } from "zod";

export const CommunitySchema = z.object({
  name: z.string().min(1, "Community name required"),
  population: z.coerce.number().positive().optional(),
  current_access_pct: z.coerce.number().min(0).max(1).optional(),
  notes: z.string().optional(),
});

export const CreateRunSchema = z.object({
  decision_question: z
    .string()
    .min(10, "Question must be at least 10 characters")
    .max(1000),
  context: z.string().max(2000).optional(),
  budget_usd: z.coerce
    .number()
    .positive("Budget must be positive")
    .max(10_000_000),
  communities: z
    .array(CommunitySchema)
    .min(1, "At least one community required"),
  objective: z.string().min(5).max(500),
  interventions: z
    .array(z.string())
    .min(1, "Select at least one intervention"),
  demo_mode: z.boolean().default(false),
});

export type CreateRunFormValues = z.infer<typeof CreateRunSchema>;
