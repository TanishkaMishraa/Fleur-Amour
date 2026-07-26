"use client";
import { motion } from "framer-motion";
import { User, Sparkles, CheckCircle, AlertCircle } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { AvatarUpload } from "@/components/features/profile/AvatarUpload";
import { ProfileForm } from "@/components/features/profile/ProfileForm";
import { useAuthStore } from "@/lib/stores/auth.store";
import { authExtendedApi } from "@/lib/api/users";
import { useState } from "react";

const anim = (i: number) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: i * 0.07, duration: 0.4, ease: [0.23, 1, 0.32, 1] as const },
});

export default function ProfilePage() {
  const { user, profile } = useAuthStore();
  const [resending, setResending] = useState(false);
  const [resent, setResent]       = useState(false);

  const resendVerification = async () => {
    if (!user?.email) return;
    setResending(true);
    try {
      await authExtendedApi.resendVerification(user.email);
      setResent(true);
    } catch {} finally { setResending(false); }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <motion.div {...anim(0)}>
        <h1 className="font-display text-display-md font-light tracking-tightest">
          My <span className="italic text-gold-gradient">Profile</span>
        </h1>
        <p className="mt-1.5 text-muted-foreground">Manage your personal information and account details.</p>
      </motion.div>

      <Tabs defaultValue="account">
        <motion.div {...anim(1)}>
          <TabsList className="mb-6">
            <TabsTrigger value="account">Account</TabsTrigger>
            <TabsTrigger value="beauty">Beauty Profile</TabsTrigger>
          </TabsList>
        </motion.div>

        {/* ── Account tab ─────────────────────────────────────────────────── */}
        <TabsContent value="account" className="space-y-6">
          {/* Avatar + basic info */}
          <motion.div {...anim(2)}>
            <Card>
              <CardHeader>
                <CardTitle>Personal information</CardTitle>
                <CardDescription>Update your name and profile photo.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <AvatarUpload />
                <Separator />
                <ProfileForm />
              </CardContent>
            </Card>
          </motion.div>

          {/* Email verification banner */}
          {!user?.is_verified && (
            <motion.div {...anim(3)}>
              <div className="flex items-start gap-4 rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5">
                <AlertCircle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-amber-400">Email not verified</p>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    Verify your email to unlock all features.
                  </p>
                </div>
                <Button variant="ghost-gold" size="sm" onClick={resendVerification}
                  loading={resending} className="shrink-0">
                  {resent ? "Sent!" : "Resend"}
                </Button>
              </div>
            </motion.div>
          )}

          {/* Account status */}
          <motion.div {...anim(4)}>
            <Card>
              <CardHeader>
                <CardTitle>Account status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div>
                    <p className="text-sm font-medium">Email</p>
                    <p className="text-xs text-muted-foreground">{user?.email}</p>
                  </div>
                  <Badge variant={user?.is_verified ? "success" : "default"}>
                    {user?.is_verified
                      ? <><CheckCircle className="h-3 w-3" /> Verified</>
                      : "Unverified"
                    }
                  </Badge>
                </div>

                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div>
                    <p className="text-sm font-medium">Account type</p>
                    <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
                  </div>
                  <Badge variant="gold">
                    <Sparkles className="h-3 w-3" />
                    {user?.role === "admin" ? "Administrator" : user?.role === "stylist" ? "Stylist" : "Member"}
                  </Badge>
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium">Member since</p>
                    <p className="text-xs text-muted-foreground">
                      {user?.created_at ? new Date(user.created_at).toLocaleDateString("en-US", {
                        month: "long", year: "numeric"
                      }) : "—"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        {/* ── Beauty Profile tab ───────────────────────────────────────────── */}
        <TabsContent value="beauty" className="space-y-6">
          <motion.div {...anim(2)}>
            <Card>
              <CardHeader>
                <CardTitle>Beauty profile</CardTitle>
                <CardDescription>
                  Your profile is used by AuraFit AI to personalise every recommendation.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {profile?.onboarding_complete ? (
                  <div className="space-y-4">
                    {[
                      { label: "Skin tone",    value: profile.skin_tone },
                      { label: "Skin type",    value: profile.skin_type },
                      { label: "Undertone",    value: profile.undertone },
                      { label: "Hair type",    value: profile.hair_type },
                      { label: "Eye color",    value: profile.eye_color },
                      { label: "Body shape",   value: profile.body_shape },
                      { label: "Budget range", value: profile.budget_range },
                    ].map(({ label, value }) => value && (
                      <div key={label} className="flex items-center justify-between border-b border-white/[0.04] py-3 last:border-0">
                        <span className="text-sm text-muted-foreground">{label}</span>
                        <span className="text-sm font-medium capitalize">{value.replace(/_/g, " ")}</span>
                      </div>
                    ))}
                    {profile.style_archetypes && profile.style_archetypes.length > 0 && (
                      <div className="pt-2">
                        <p className="text-sm text-muted-foreground mb-2">Style archetypes</p>
                        <div className="flex flex-wrap gap-2">
                          {profile.style_archetypes.map((a) => (
                            <Badge key={a} variant="gold" className="capitalize">{a}</Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    <Button variant="ghost-gold" size="sm" className="mt-2">
                      Edit beauty profile
                    </Button>
                  </div>
                ) : (
                  <div className="text-center py-10 space-y-4">
                    <div className="mx-auto h-14 w-14 rounded-2xl bg-brand-gold/10 border border-brand-gold/20 flex items-center justify-center">
                      <User className="h-7 w-7 text-brand-gold/60" />
                    </div>
                    <div>
                      <p className="font-medium text-foreground">Complete your beauty profile</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Tell us about your skin, hair, and style to unlock personalised AI recommendations.
                      </p>
                    </div>
                    <Button variant="gold">Start Beauty Quiz</Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
