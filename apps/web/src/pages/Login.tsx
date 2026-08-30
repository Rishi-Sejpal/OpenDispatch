import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { login } from '../lib/auth';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});
type FormData = z.infer<typeof schema>;

export default function Login() {
  const nav = useNavigate();
  const [loading, setLoading] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      await login(data.email, data.password);
      toast.success('Signed in');
      nav('/');
    } catch (e) {
      toast.error((e as Error).message || 'Sign in failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-base">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-96 bg-bg-panel border border-bg-line rounded-lg p-6 space-y-4"
      >
        <div>
          <div className="text-2xl font-semibold">OpenDispatch</div>
          <div className="text-sm text-slate-400">Sign in to your dispatch account</div>
        </div>
        <div>
          <label className="label" htmlFor="login-email">
            Email
          </label>
          <input id="login-email" className="input" type="email" autoFocus {...register('email')} />
          {errors.email && <p className="text-xs text-rose-400 mt-1">{errors.email.message}</p>}
        </div>
        <div>
          <label className="label" htmlFor="login-password">
            Password
          </label>
          <input id="login-password" className="input" type="password" {...register('password')} />
          {errors.password && (
            <p className="text-xs text-rose-400 mt-1">{errors.password.message}</p>
          )}
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
        <div className="text-center text-sm text-slate-400">
          New here?{' '}
          <Link to="/register" className="text-accent hover:underline">
            Create an account
          </Link>
        </div>
        <div className="text-center text-[10px] text-slate-600">
          Default: dispatch@opendispatch.example.com / dispatch123!
        </div>
      </form>
    </div>
  );
}
