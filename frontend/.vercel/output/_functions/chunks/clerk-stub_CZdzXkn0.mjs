const SignIn = () => null;
const SignUp = () => null;
const UserButton = () => null;
const clerkMiddleware = () => {
  throw new Error("Clerk is not configured (PUBLIC_CLERK_PUBLISHABLE_KEY is missing)");
};

export { SignIn, SignUp, UserButton, clerkMiddleware };
