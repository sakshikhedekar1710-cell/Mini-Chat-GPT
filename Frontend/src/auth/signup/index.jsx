import React, { useEffect, useState } from 'react';
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { useDispatch } from "react-redux";
import { axiosClient } from "../../libs/axiosClient.js";
import { setUserData } from "../../redux/slices/userSlice.js";
import { isRequiredFieldValuesPassed } from "../../utils/helpers.js";

function SignupPage() {
    const navigate = useNavigate();
    const dispatch = useDispatch();

    const [state, setState] = useState({});
    const [loading, setLoading] = useState(false);
    const [disabled, setDisabled] = useState(true);

    // ✅ ADD THIS FUNCTION (VERY IMPORTANT)
    const handleChange = (e) => {
        setState({
            ...state,
            [e.target.name]: e.target.value
        });
    };

    const register = async () => {
        try {
            setLoading(true);

            const response = await axiosClient.post("/auth/register/", state);

            toast.success("Registration successful!");

            dispatch(setUserData(response.data));

            navigate("/login");

        } catch (error) {
            console.error("REGISTER ERROR:", error);

            if (error.response) {
                toast.error(JSON.stringify(error.response.data));
            } else {
                toast.error("Server not reachable");
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const requiredFields = ["first_name", "last_name", "email", "password", "c_password"];
        setDisabled(!isRequiredFieldValuesPassed(state, requiredFields, "eq"));
    }, [state]);

    return (
        <div className="h-[100vh] flex justify-center items-center">
            <div>
                <h1 className="font-bold text-[25px] text-center mb-5">Signup Page</h1>

                <div className="input-group">
                    <label>First Name*</label>
                    <input
                        type="text"
                        placeholder="First Name"
                        name="first_name"
                        onChange={handleChange}
                    />
                </div>

                <div className="input-group">
                    <label>Last Name*</label>
                    <input
                        type="text"
                        placeholder="Last Name"
                        name="last_name"
                        onChange={handleChange}
                    />
                </div>

                <div className="input-group">
                    <label>Email*</label>
                    <input
                        type="text"
                        placeholder="Email"
                        name="email"
                        onChange={handleChange}
                    />
                </div>

                <div className="input-group">
                    <label>Password*</label>
                    <input
                        type="password"
                        placeholder="Password"
                        name="password"
                        onChange={handleChange}
                    />
                </div>

                <div className="input-group">
                    <label>Confirm Password*</label>
                    <input
                        type="password"
                        placeholder="Confirm Password"
                        name="c_password"
                        onChange={handleChange}
                    />
                </div>

                <div className="flex justify-center flex-col mt-4">
                    <button
                        className="bg-blue-500 text-white px-3 py-2 rounded-md"
                        disabled={disabled || loading}
                        onClick={register}
                    >
                        {loading ? "Loading..." : "Register"}
                    </button>

                    <span className="text-[13px] text-center mt-4">
                        Already have an account?
                        <u className="cursor-pointer ml-2" onClick={() => navigate('/login')}>
                            Login
                        </u>
                    </span>
                </div>
            </div>
        </div>
    );
}

export default SignupPage;
