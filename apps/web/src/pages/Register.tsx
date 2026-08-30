import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { register as registerUser, login } from '../lib/auth';
import { extractError } from '../lib/api';

const schema = z.object({
  email: z.string().email(),
  full_name: z.string().min(1, 'Required'),
  password: z.string().min(8, 'Min 8 chars'),
  organization_name: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

export default function Register() {
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
      await registerUser(data.email, data.password, data.full_name, data.organization_name);
      await login(data.email, data.password);
      toast.success('Account created');
      nav('/');
    } catch (e) {
      toast.error(extractError(e).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-base">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-[28rem] bg-bg-panel border border-bg-line rounded-lg p-6 space-y-4"
      >
        <div>
          <div className="text-2xl font-semibold">Create an account</div>
          <div className="text-sm text-slate-400">Start dispatching flight plans</div>
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" type="email" {...register('email')} />
          {errors.email && <p className="text-xs text-rose-400 mt-1">{errors.email.message}</p>}
        </div>
        <div>
          <label className="label">Full name</label>
          <input className="input" {...register('full_name')} />
          {errors.full_name && <p className="text-xs text-rose-400 mt-1">{errors.full_name.message}</p>}
        </div>
        <div>
          <label className="label">Password</label>
          <input className="input" type="password" {...register('password')} />
          {errors.password && <p className="text-xs text-rose-400 mt-1">{errors.password.message}</p>}
        </div>
        <div>
          <label className="label">Organization (optional)</label>
          <input className="input" placeholder="e.g. Acme Airlines" {...register('organization_name')} />
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? 'Creating…' : 'Create account'}
        </button>
        <div className="text-center text-sm text-slate-400">
          Already have one?{' '}
          <Link to="/login" className="text-accent hover:underline">
            Sign in
          </Link>
        </div>
      </form>
    </div>
  );
}
